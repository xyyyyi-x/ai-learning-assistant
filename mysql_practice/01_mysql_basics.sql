CREATE DATABASE IF NOT EXISTS ai_learning_practice
CHARACTER SET utf8mb4
COLLATE utf8mb4_0900_ai_ci;

USE ai_learning_practice;

CREATE TABLE IF NOT EXISTS tasks (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    title VARCHAR(50) NOT NULL,
    completed BOOLEAN NOT NULL DEFAULT FALSE,
    priority TINYINT UNSIGNED NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    CONSTRAINT chk_tasks_title
        CHECK (CHAR_LENGTH(TRIM(title)) BETWEEN 1 AND 50),
    CONSTRAINT chk_tasks_priority
        CHECK (priority BETWEEN 1 AND 3)
) ENGINE=InnoDB;

TRUNCATE TABLE tasks;

INSERT INTO tasks (title, completed, priority)
VALUES
    ('学习MySQL建表', FALSE, 3),
    ('复习HTTP状态码', TRUE, 1),
    ('练习参数化SQL', FALSE, 2),
    ('临时任务', FALSE, 1);

SELECT * FROM tasks ORDER BY id;

SELECT id, title, completed, priority
FROM tasks
WHERE completed = FALSE
ORDER BY priority DESC, id ASC;

SELECT priority, COUNT(*) AS task_count
FROM tasks
GROUP BY priority
ORDER BY priority;

UPDATE tasks
SET completed = TRUE
WHERE title = '学习MySQL建表';

DELETE FROM tasks
WHERE title = '临时任务';

SELECT * FROM tasks ORDER BY id;

START TRANSACTION;

UPDATE tasks
SET priority = 3
WHERE title = '复习HTTP状态码';

SELECT title, priority
FROM tasks
WHERE title = '复习HTTP状态码';

ROLLBACK;

SELECT title, priority
FROM tasks
WHERE title = '复习HTTP状态码';

SHOW CREATE TABLE tasks;
