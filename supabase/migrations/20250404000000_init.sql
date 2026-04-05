-- Profiles mirror auth.users (created via trigger).
create table if not exists public.profiles (
  id uuid references auth.users on delete cascade primary key,
  email text,
  full_name text,
  updated_at timestamptz not null default now()
);

-- Telemetry time-series table
create table if not exists public.telemetry (
  id uuid primary key default gen_random_uuid(),
  ts timestamptz not null default now(),
  locomotive_id text not null default 'loco-1',
  state text not null,

  speed_kmh double precision not null,
  traction_power_kw double precision not null,
  engine_temp_c double precision not null,
  transformer_temp_c double precision not null,
  brake_pipe_pressure_bar double precision not null,
  voltage_v double precision not null,
  current_a double precision not null,
  vibration_mm_s double precision not null,
  fuel_level_pct double precision not null,
  fault_code text,

  health_index double precision
);

create index if not exists ix_telemetry_loco_ts on public.telemetry (locomotive_id, ts);

-- Optional: convert to TimescaleDB hypertable if extension is available
-- SELECT create_hypertable('public.telemetry', 'ts', if_not_exists => TRUE);

-- Alerts table
create table if not exists public.alerts (
  id uuid primary key default gen_random_uuid(),
  ts timestamptz not null default now(),
  locomotive_id text not null default 'loco-1',
  severity text not null,        -- critical / warning / info
  code text not null,
  title text not null,
  detail text,
  recommendation text,
  acknowledged boolean not null default false
);

create index if not exists ix_alerts_loco_ts on public.alerts (locomotive_id, ts);

-- Items (simple CRUD, kept from original)
create table if not exists public.items (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users on delete cascade,
  title text not null,
  created_at timestamptz not null default now()
);

create index if not exists items_user_id_created_at_idx on public.items (user_id, created_at desc);

-- RLS
alter table public.profiles enable row level security;
alter table public.items enable row level security;
alter table public.telemetry enable row level security;
alter table public.alerts enable row level security;

-- Profiles policies
create policy "profiles_select_own"
  on public.profiles for select
  using (auth.uid() = id);

create policy "profiles_update_own"
  on public.profiles for update
  using (auth.uid() = id);

-- Items policies
create policy "items_select_own"
  on public.items for select
  using (auth.uid() = user_id);

create policy "items_insert_own"
  on public.items for insert
  with check (auth.uid() = user_id);

create policy "items_update_own"
  on public.items for update
  using (auth.uid() = user_id);

create policy "items_delete_own"
  on public.items for delete
  using (auth.uid() = user_id);

-- Telemetry: read-only for authenticated users (service role writes)
create policy "telemetry_select_authenticated"
  on public.telemetry for select
  using (auth.role() = 'authenticated');

-- Alerts: read for authenticated, acknowledge via API
create policy "alerts_select_authenticated"
  on public.alerts for select
  using (auth.role() = 'authenticated');

-- Auto-create profile on signup
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles (id, email, full_name)
  values (
    new.id,
    new.email,
    coalesce(new.raw_user_meta_data->>'full_name', '')
  );
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();
