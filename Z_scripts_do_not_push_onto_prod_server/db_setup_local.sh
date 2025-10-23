sudo -u postgres psql << 'EOF'
-- Development
CREATE DATABASE scrapper_db;
CREATE USER scrapper_user WITH PASSWORD 'password123';
GRANT ALL PRIVILEGES ON DATABASE scrapper_db TO scrapper_user;

-- Testing  
CREATE DATABASE scrapper_test;
CREATE USER scrapper_test_user WITH PASSWORD 'test_password';
GRANT ALL PRIVILEGES ON DATABASE scrapper_test TO scrapper_test_user;

-- Production
CREATE DATABASE scrapper_prod;
CREATE USER scrapper_prod_user WITH PASSWORD 'secure_prod_password';
GRANT ALL PRIVILEGES ON DATABASE scrapper_prod TO scrapper_prod_user;
\q
EOF