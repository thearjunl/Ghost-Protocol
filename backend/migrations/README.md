# Database Migrations

This directory contains SQL migration scripts for the GhostProtocol database.

## Migration Files

- `001_initial_schema.sql` - Creates the initial identities table with indexes and triggers

## Running Migrations

### Option 1: Using Supabase Dashboard

1. Log in to your Supabase project dashboard
2. Navigate to the SQL Editor
3. Copy and paste the contents of each migration file in order
4. Execute the SQL

### Option 2: Using Supabase CLI

```bash
# Install Supabase CLI
npm install -g supabase

# Link to your project
supabase link --project-ref your-project-ref

# Run migrations
supabase db push
```

### Option 3: Using the Migration Script

```bash
cd backend
python migrate.py
```

## Creating New Migrations

1. Create a new file with the next sequential number: `00X_description.sql`
2. Write your SQL migration
3. Test locally before applying to production
4. Document the migration in this README

## Migration Naming Convention

Format: `NNN_description.sql`
- `NNN` - Three-digit sequential number (001, 002, etc.)
- `description` - Brief description using snake_case

Examples:
- `001_initial_schema.sql`
- `002_add_audit_log_table.sql`
- `003_add_user_roles.sql`

## Rollback Strategy

Each migration should include comments explaining how to rollback if needed.
For destructive changes, always backup data first.
