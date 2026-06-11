-- =============================================================================
-- FraudPulse — link Supabase Auth to the app's profiles table.
--
-- Run ONCE in the Supabase SQL editor (Dashboard -> SQL Editor -> New query).
-- Safe to re-run: every statement is idempotent.
--
-- Supabase Auth owns auth.users (credentials, password hashing, JWT issuance).
-- The app's public.profiles table carries role / display name / active flag.
-- This script ties profiles.id to auth.users.id and auto-creates a profile row
-- whenever an admin adds a user, so the two stay in sync.
-- =============================================================================

-- 1. profiles.id references auth.users(id). The UUIDs already line up by design.
alter table public.profiles
  drop constraint if exists profiles_id_fkey;
alter table public.profiles
  add constraint profiles_id_fkey
  foreign key (id) references auth.users (id) on delete cascade;

-- 2. On every new auth user, insert a matching profile (defaults: FRAUD_ANALYST/active).
--    full_name / role can be supplied via the user's metadata when created.
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles (id, role, full_name, is_active)
  values (
    new.id,
    coalesce(new.raw_user_meta_data ->> 'role', 'FRAUD_ANALYST'),
    coalesce(new.raw_user_meta_data ->> 'full_name', split_part(new.email, '@', 1)),
    true
  )
  on conflict (id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- 3. Backfill profiles for any users created before this trigger existed.
insert into public.profiles (id, role, full_name, is_active)
select u.id,
       'FRAUD_ANALYST',
       coalesce(u.raw_user_meta_data ->> 'full_name', split_part(u.email, '@', 1)),
       true
from auth.users u
left join public.profiles p on p.id = u.id
where p.id is null;
