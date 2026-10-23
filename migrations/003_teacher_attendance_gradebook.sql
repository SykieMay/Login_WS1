-- Add storage for teacher attendance and gradebook entries.

CREATE TABLE IF NOT EXISTS teacher_attendance (
    id BIGINT NOT NULL AUTO_INCREMENT,
    teacher_id BIGINT NOT NULL,
    student_id BIGINT NOT NULL,
    subject_id BIGINT NOT NULL,
    attendance_date DATE NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_teacher_attendance_student_subject_date
        (student_id, subject_id, attendance_date),
    KEY idx_teacher_attendance_teacher_date (teacher_id, attendance_date),
    KEY idx_teacher_attendance_student (student_id)
);

CREATE TABLE IF NOT EXISTS teacher_gradebook (
    id BIGINT NOT NULL AUTO_INCREMENT,
    teacher_id BIGINT NOT NULL,
    student_id BIGINT NOT NULL,
    subject_id BIGINT NOT NULL,
    assessment VARCHAR(120) NOT NULL,
    grade DECIMAL(5,2) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_teacher_gradebook_student_subject_assessment
        (student_id, subject_id, assessment),
    KEY idx_teacher_gradebook_teacher (teacher_id),
    KEY idx_teacher_gradebook_student (student_id)
);
