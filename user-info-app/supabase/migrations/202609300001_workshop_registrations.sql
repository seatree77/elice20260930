create table public.workshop_registrations (
    id uuid primary key,
    name text not null check (char_length(btrim(name)) between 1 and 100),
    email text not null check (char_length(email) <= 254 and email ~ '^[^[:space:]@]+@[^[:space:]@]+\.[^[:space:]@]+$'),
    session text not null check (session in ('1', '2', '3')),
    created_at timestamptz not null default now()
);
create table public.workshop_rate_limits (
    fingerprint text not null,
    bucket bigint not null,
    requests integer not null,
    primary key (fingerprint, bucket)
);
alter table public.workshop_registrations enable row level security;
alter table public.workshop_rate_limits enable row level security;
revoke all on public.workshop_registrations, public.workshop_rate_limits from anon, authenticated;
grant select, insert on public.workshop_registrations to service_role;
grant select, insert, update, delete on public.workshop_rate_limits to service_role;

create function public.submit_workshop_registration(
    p_name text, p_email text, p_session text, p_request_id uuid, p_fingerprint text
) returns uuid
language plpgsql security invoker set search_path = ''
as $$
declare
    current_bucket bigint := floor(extract(epoch from now()) / 600)::bigint;
    request_count integer;
begin
    if p_fingerprint !~ '^[a-f0-9]{64}$' then
        raise exception 'invalid_fingerprint';
    end if;
    perform pg_advisory_xact_lock(hashtextextended(p_fingerprint, 0));
    if exists (select 1 from public.workshop_registrations where id = p_request_id) then
        return p_request_id;
    end if;
    insert into public.workshop_rate_limits (fingerprint, bucket, requests)
    values (p_fingerprint, current_bucket, 1)
    on conflict (fingerprint, bucket) do update
    set requests = public.workshop_rate_limits.requests + 1
    returning requests into request_count;
    if request_count > 10 then
        raise exception 'registration_rate_limit';
    end if;
    delete from public.workshop_rate_limits where fingerprint = p_fingerprint and bucket < current_bucket;
    insert into public.workshop_registrations(id, name, email, session)
    values (p_request_id, btrim(p_name), btrim(p_email), p_session)
    on conflict (id) do nothing;
    return p_request_id;
end;
$$;
revoke all on function public.submit_workshop_registration(text,text,text,uuid,text) from public, anon, authenticated;
grant execute on function public.submit_workshop_registration(text,text,text,uuid,text) to service_role;
