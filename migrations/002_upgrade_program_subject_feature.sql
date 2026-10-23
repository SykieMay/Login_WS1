-- Repair/complete the program-subject feature schema in an existing database.
-- The app's older `subjects` table may have an unrelated legacy structure.

CREATE TABLE IF NOT EXISTS programs (
    id BIGINT NOT NULL AUTO_INCREMENT,
    name VARCHAR(120) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_programs_name (name)
);

CREATE TABLE IF NOT EXISTS program_subjects (
    id BIGINT NOT NULL AUTO_INCREMENT,
    program_id BIGINT NOT NULL,
    teacher_id BIGINT NOT NULL,
    name VARCHAR(120) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_program_subjects_program_name (program_id, name),
    KEY idx_program_subjects_teacher (teacher_id),
    KEY idx_program_subjects_program (program_id)
);

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS program_id BIGINT NULL;

ALTER TABLE assignments
    ADD COLUMN IF NOT EXISTS subject_id BIGINT NULL;

ALTER TABLE lesson_plans
    ADD COLUMN IF NOT EXISTS subject_id BIGINT NULL;
