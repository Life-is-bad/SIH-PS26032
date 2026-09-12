-- =====================================================================
-- SIH Problem Statement 26032
-- Farmer Slot Booking & Real-Time Queue Management System
-- Target: MySQL 8.0+ (deployed on Railway MySQL 9.4)
--
-- Railway deploy version — no DROP/CREATE DATABASE/USE statements,
-- since Railway already provisions its own database and this runs
-- directly against it via the connection string.
-- =====================================================================

CREATE TABLE users (
    user_id         BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    role            ENUM('farmer', 'officer') NOT NULL,
    full_name       VARCHAR(100) NOT NULL,
    phone_number    VARCHAR(15) NOT NULL,
    email           VARCHAR(120) NULL,
    password_hash   VARCHAR(255) NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                        ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT uq_users_phone UNIQUE (phone_number)
) ENGINE=InnoDB;

CREATE TABLE counters (
    counter_id      INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    counter_name    VARCHAR(100) NOT NULL,
    location_desc   VARCHAR(255) NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                        ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE slots (
    slot_id         BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    counter_id      INT UNSIGNED NOT NULL,
    slot_date       DATE NOT NULL,
    start_time      TIME NOT NULL,
    end_time        TIME NOT NULL,
    capacity        SMALLINT UNSIGNED NOT NULL,
    booked_count    SMALLINT UNSIGNED NOT NULL DEFAULT 0,
    created_by      BIGINT UNSIGNED NOT NULL,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                        ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_slots_counter FOREIGN KEY (counter_id)
        REFERENCES counters(counter_id) ON DELETE RESTRICT,
    CONSTRAINT fk_slots_created_by FOREIGN KEY (created_by)
        REFERENCES users(user_id) ON DELETE RESTRICT,
    CONSTRAINT chk_slots_time CHECK (end_time > start_time),
    CONSTRAINT chk_slots_capacity CHECK (booked_count <= capacity)
) ENGINE=InnoDB;

CREATE INDEX idx_slots_counter_date ON slots (counter_id, slot_date);

CREATE TABLE bookings (
    booking_id      BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    farmer_id       BIGINT UNSIGNED NOT NULL,
    slot_id         BIGINT UNSIGNED NOT NULL,
    status          ENUM('booked', 'cancelled', 'rescheduled', 'completed')
                        NOT NULL DEFAULT 'booked',
    booking_time    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    produce_type    VARCHAR(80) NULL,
    qr_token        VARCHAR(64) NULL,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                        ON UPDATE CURRENT_TIMESTAMP,

    active_lock BIGINT UNSIGNED GENERATED ALWAYS AS (
        IF(status = 'booked', farmer_id, NULL)
    ) STORED,

    CONSTRAINT fk_bookings_farmer FOREIGN KEY (farmer_id)
        REFERENCES users(user_id) ON DELETE RESTRICT,
    CONSTRAINT fk_bookings_slot FOREIGN KEY (slot_id)
        REFERENCES slots(slot_id) ON DELETE RESTRICT,
    CONSTRAINT uq_bookings_active UNIQUE (slot_id, active_lock),
    CONSTRAINT uq_bookings_qr_token UNIQUE (qr_token)
) ENGINE=InnoDB;

CREATE INDEX idx_bookings_farmer ON bookings (farmer_id);
CREATE INDEX idx_bookings_slot ON bookings (slot_id);
CREATE INDEX idx_bookings_time ON bookings (booking_time);

CREATE TABLE queue_status (
    queue_id            BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    booking_id          BIGINT UNSIGNED NOT NULL,
    queue_position       SMALLINT UNSIGNED NULL,
    estimated_wait_mins  SMALLINT UNSIGNED NULL,
    check_in_status      ENUM('waiting', 'checked_in', 'in_service', 'served', 'no_show')
                             NOT NULL DEFAULT 'waiting',
    checked_in_at        TIMESTAMP NULL,
    checked_in_by        BIGINT UNSIGNED NULL,
    created_at           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                             ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_queue_booking FOREIGN KEY (booking_id)
        REFERENCES bookings(booking_id) ON DELETE CASCADE,
    CONSTRAINT fk_queue_officer FOREIGN KEY (checked_in_by)
        REFERENCES users(user_id) ON DELETE SET NULL,
    CONSTRAINT uq_queue_booking UNIQUE (booking_id)
) ENGINE=InnoDB;

CREATE INDEX idx_queue_status ON queue_status (check_in_status);

CREATE TABLE booking_history (
    history_id       BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    old_booking_id    BIGINT UNSIGNED NOT NULL,
    new_booking_id    BIGINT UNSIGNED NOT NULL,
    reason           VARCHAR(255) NULL,
    changed_by        BIGINT UNSIGNED NOT NULL,
    changed_at        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_history_old_booking FOREIGN KEY (old_booking_id)
        REFERENCES bookings(booking_id) ON DELETE RESTRICT,
    CONSTRAINT fk_history_new_booking FOREIGN KEY (new_booking_id)
        REFERENCES bookings(booking_id) ON DELETE RESTRICT,
    CONSTRAINT fk_history_changed_by FOREIGN KEY (changed_by)
        REFERENCES users(user_id) ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE INDEX idx_history_old_booking ON booking_history (old_booking_id);

DELIMITER $$

CREATE TRIGGER trg_bookings_after_insert
AFTER INSERT ON bookings
FOR EACH ROW
BEGIN
    IF NEW.status = 'booked' THEN
        UPDATE slots SET booked_count = booked_count + 1
        WHERE slot_id = NEW.slot_id;
    END IF;
END$$

CREATE TRIGGER trg_bookings_after_update
AFTER UPDATE ON bookings
FOR EACH ROW
BEGIN
    IF OLD.status <> 'booked' AND NEW.status = 'booked' THEN
        UPDATE slots SET booked_count = booked_count + 1
        WHERE slot_id = NEW.slot_id;
    ELSEIF OLD.status = 'booked' AND NEW.status <> 'booked' THEN
        UPDATE slots SET booked_count = booked_count - 1
        WHERE slot_id = NEW.slot_id;
    END IF;
END$$

DELIMITER ;
