-- SQL commands to manage admin users in TicketRush
-- Run these commands directly in your database console (e.g., Render's database dashboard)

-- 1. Promote a user to admin by email
UPDATE "user" 
SET is_admin = true 
WHERE email = 'hello@saunders-simmons.co.uk';

-- 2. Verify the user was promoted
SELECT id, email, first_name, last_name, business_name, is_admin 
FROM "user" 
WHERE email = 'hello@saunders-simmons.co.uk';

-- 3. List all admin users
SELECT id, email, first_name, last_name, business_name 
FROM "user" 
WHERE is_admin = true;

-- 4. Remove admin privileges (if needed)
-- UPDATE "user" 
-- SET is_admin = false 
-- WHERE email = 'hello@saunders-simmons.co.uk';