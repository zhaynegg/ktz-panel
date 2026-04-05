-- Allow FastAPI dev mode (DEV_USER_ID) without a matching auth.users row.
alter table public.items drop constraint if exists items_user_id_fkey;
