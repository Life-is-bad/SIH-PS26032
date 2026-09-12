-- =====================================================================
-- SIH Problem Statement 26032
-- Farmer Slot Booking & Real-Time Queue Management System
-- Database: SIH_PS26032
-- Target: MySQL 8.0+
--
-- HOW TO RUN:
--   mysql -u root -p < schema.sql
--
-- DESIGN NOTES (read before extending this schema):
--   1. Double-booking prevention uses a generated column + composite
--      UNIQUE index trick (see `bookings.active_lock` below). This is
--      the non-obvious bit — read the comment there before touching it.
--   2. `slots.booked_count` is a denormalized counter kept in sync by
--      triggers, for fast reads on the live queue dashboard. It is NOT
--      the concurrency-safety mechanism — your application code must
--      still use `SELECT ... FOR UPDATE` inside a transaction when
--      inserting a booking, to avoid a race condition where two
--      farmers both book the last seat at the same time. Trigger-only
--      enforcement is not safe under concurrent writes.
--   3. Rescheduling is append-only: the old booking row is marked
--      'rescheduled' (never deleted/overwritten), a new booking row is
--      created, and `booking_history` links the two. This gives a free
--      audit trail.
--   4. Trade-off flags (hackathon vs. production) are marked inline
--      with "-- TRADE-OFF:" comments.
-- =====================================================================

USE SIH_PS26032;

-- ---------------------------------------------------------------------
-- 1. USERS
-- Single table for both roles (Farmer / Procurement Officer) rather than
-- two separate tables. Reasoning: both roles share the same auth fields
-- (login, password hash, phone) and RBAC is enforced in the app layer
-- via the `role` column + JWT claims, not via separate schemas.
-- TRADE-OFF: a fully normalized design might split role-specific fields
-- (e.g. officer's assigned counter) into a separate `officer_profile`
-- table. We keep it flat here since the hackathon scope only needs one
-- optional officer attribute; add a profile table only if that grows.
-- ---------------------------------------------------------------------
CREATE TABLE users (
    user_id         BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    role            ENUM('farmer', 'officer') NOT NULL,
    full_name       VARCHAR(100) NOT NULL,
    phone_number    VARCHAR(15) NOT NULL,          -- used for login + SMS/IVR alerts
    email           VARCHAR(120) NULL,
    password_hash   VARCHAR(255) NOT NULL,         -- bcrypt hash via passlib, never plaintext
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,  -- soft-disable instead of deleting accounts
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                        ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT uq_users_phone UNIQUE (phone_number)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 2. COUNTERS  (a.k.a. procurement locations)
-- Slots "belong to a location/counter", so this is a proper parent
-- table rather than a repeated free-text location string on `slots`.
-- ---------------------------------------------------------------------
CREATE TABLE counters (
    counter_id      INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    counter_name    VARCHAR(100) NOT NULL,
    location_desc   VARCHAR(255) NOT NULL,   -- village/mandi/address text for farmers
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                        ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 3. SLOTS
-- A bookable time window at a counter, with a hard capacity limit.
-- `booked_count` is denormalized (see file-level note #2 above).
-- ---------------------------------------------------------------------
CREATE TABLE slots (
    slot_id         BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    counter_id      INT UNSIGNED NOT NULL,
    slot_date       DATE NOT NULL,
    start_time      TIME NOT NULL,
    end_time        TIME NOT NULL,
    capacity        SMALLINT UNSIGNED NOT NULL,
    booked_count    SMALLINT UNSIGNED NOT NULL DEFAULT 0,   -- kept in sync by triggers below
    created_by      BIGINT UNSIGNED NOT NULL,                -- officer who created the slot
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

-- Composite index: the dashboard's most common query is "show slots for
-- this counter on this date", so index in that order.
CREATE INDEX idx_slots_counter_date ON slots (counter_id, slot_date);

-- ---------------------------------------------------------------------
-- 4. BOOKINGS
-- One row per booking attempt. Cancelling/rescheduling updates `status`
-- rather than deleting the row, so history is preserved.
-- ---------------------------------------------------------------------
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

    -- ---------------------------------------------------------------
    -- THE DOUBLE-BOOKING TRICK:
    -- This generated column collapses to `farmer_id` only when the
    -- booking is currently active ('booked'); otherwise it's NULL.
    -- MySQL unique indexes treat every NULL as distinct (no conflict),
    -- so a farmer can freely rebook the same slot after a cancellation,
    -- but cannot hold two simultaneous active bookings for one slot.
    -- ---------------------------------------------------------------
    active_lock BIGINT UNSIGNED GENERATED ALWAYS AS (
        IF(status = 'booked', farmer_id, NULL)
    ) STORED,

    CONSTRAINT fk_bookings_farmer FOREIGN KEY (farmer_id)
        REFERENCES users(user_id) ON DELETE RESTRICT,
    CONSTRAINT fk_bookings_slot FOREIGN KEY (slot_id)
        REFERENCES slots(slot_id) ON DELETE RESTRICT,
    CONSTRAINT uq_bookings_active UNIQUE (slot_id, active_lock)
) ENGINE=InnoDB;

-- Explicitly required by the spec: indexes on farmer_id, slot_id, booking_time.
-- (uq_bookings_active above already indexes slot_id as its leading column,
-- but we add a standalone one too since not every query filters by both
-- columns in that order — e.g. "all slots with any bookings".)
CREATE INDEX idx_bookings_farmer ON bookings (farmer_id);
CREATE INDEX idx_bookings_slot ON bookings (slot_id);
CREATE INDEX idx_bookings_time ON bookings (booking_time);

-- ---------------------------------------------------------------------
-- 5. QUEUE_STATUS
-- Live queue tracking, separate from booking status (see file-level
-- note #3). One row per booking, created at check-in time or pre-seeded
-- when the booking is made.
-- ---------------------------------------------------------------------
CREATE TABLE queue_status (
    queue_id            BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    booking_id          BIGINT UNSIGNED NOT NULL,
    queue_position       SMALLINT UNSIGNED NULL,     -- NULL until checked in
    estimated_wait_mins  SMALLINT UNSIGNED NULL,      -- recalculated as queue moves
    check_in_status      ENUM('waiting', 'checked_in', 'in_service', 'served', 'no_show')
                             NOT NULL DEFAULT 'waiting',
    checked_in_at        TIMESTAMP NULL,
    checked_in_by        BIGINT UNSIGNED NULL,        -- officer who scanned/checked in the farmer
    created_at           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                             ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_queue_booking FOREIGN KEY (booking_id)
        REFERENCES bookings(booking_id) ON DELETE CASCADE,
    CONSTRAINT fk_queue_officer FOREIGN KEY (checked_in_by)
        REFERENCES users(user_id) ON DELETE SET NULL,
    CONSTRAINT uq_queue_booking UNIQUE (booking_id)   -- 1:1 with bookings
) ENGINE=InnoDB;

CREATE INDEX idx_queue_status ON queue_status (check_in_status);

-- ---------------------------------------------------------------------
-- 6. BOOKING_HISTORY
-- Append-only audit log for reschedules (and optionally cancellations).
-- Never updated after insert — that's what makes it a real audit trail.
-- TRADE-OFF: for a hackathon demo, logging just reschedules is enough
-- to show judges the feature works. Logging every status change too
-- would be more "production-grade" but isn't needed to prove the concept.
-- ---------------------------------------------------------------------
CREATE TABLE booking_history (
    history_id       BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    old_booking_id    BIGINT UNSIGNED NOT NULL,
    new_booking_id    BIGINT UNSIGNED NOT NULL,
    reason           VARCHAR(255) NULL,
    changed_by        BIGINT UNSIGNED NOT NULL,   -- farmer or officer who triggered it
    changed_at        TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_history_old_booking FOREIGN KEY (old_booking_id)
        REFERENCES bookings(booking_id) ON DELETE RESTRICT,
    CONSTRAINT fk_history_new_booking FOREIGN KEY (new_booking_id)
        REFERENCES bookings(booking_id) ON DELETE RESTRICT,
    CONSTRAINT fk_history_changed_by FOREIGN KEY (changed_by)
        REFERENCES users(user_id) ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE INDEX idx_history_old_booking ON booking_history (old_booking_id);

-- =====================================================================
-- TRIGGERS: keep slots.booked_count in sync with bookings.status
-- Reminder (see file-level note #2): these keep the counter accurate
-- for READS. Your FastAPI insert endpoint must still lock the slot row
-- with `SELECT ... FOR UPDATE` and check capacity before inserting —
-- triggers fire AFTER the row exists and cannot reject the insert that
-- caused it.
-- =====================================================================
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
    -- booking just became active (rare, but handle it: e.g. reinstated)
    IF OLD.status <> 'booked' AND NEW.status = 'booked' THEN
        UPDATE slots SET booked_count = booked_count + 1
        WHERE slot_id = NEW.slot_id;
    -- booking just left the active state (cancelled/rescheduled/completed)
    ELSEIF OLD.status = 'booked' AND NEW.status <> 'booked' THEN
        UPDATE slots SET booked_count = booked_count - 1
        WHERE slot_id = NEW.slot_id;
    END IF;
END$$

DELIMITER ;

-- =====================================================================
-- END OF SCHEMA
-- =====================================================================
