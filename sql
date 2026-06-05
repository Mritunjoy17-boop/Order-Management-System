CREATE TABLE customers (
    customer_id INT AUTO_INCREMENT PRIMARY KEY,

    business_name VARCHAR(255) NOT NULL,
    contact_person_name VARCHAR(255) NOT NULL,
    warehouse_name VARCHAR(255) NOT NULL,

    phone_number VARCHAR(20) NOT NULL,
    whatsapp_number VARCHAR(20),

    alternate_phone VARCHAR(20),

    email VARCHAR(255),

    address TEXT,
    city VARCHAR(100),
    region_id INT,

    gstin VARCHAR(50),
    pin_code VARCHAR(10),

    is_active TINYINT DEFAULT 1,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE regions (
    region_id INT AUTO_INCREMENT PRIMARY KEY,
    region_name VARCHAR(255) NOT NULL
);

CREATE TABLE orders (
    order_id INT AUTO_INCREMENT PRIMARY KEY,

    order_number VARCHAR(50) UNIQUE,

    customer_id INT NOT NULL,

    order_status ENUM(
        'created',
        'accepted',
        'fulfilled',
        'completed'
    ) DEFAULT 'created',

    total_items INT DEFAULT 0,
    total_quantity INT DEFAULT 0,
    total_amount DECIMAL(10, 2) DEFAULT 0.00,
    sales_agent VARCHAR(100),

    is_invoiced TINYINT DEFAULT 0,

    notes TEXT,
    image_url TEXT,

    created_by VARCHAR(100),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE order_items (
    order_item_id INT AUTO_INCREMENT PRIMARY KEY,

    order_id INT NOT NULL,
    product_code VARCHAR(50) NOT NULL,

    quantity INT NOT NULL,
    price_per_unit DECIMAL(10,2) NOT NULL,
    total_price DECIMAL(10,2) NOT NULL,

    FOREIGN KEY (order_id) REFERENCES orders(order_id),
    FOREIGN KEY (product_code) REFERENCES products(product_code)
);

