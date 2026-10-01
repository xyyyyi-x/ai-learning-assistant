# D23 MySQL基础验证

- MySQL版本：8.0.45
- 数据库名称：ai_learning_practice
- 表名称：tasks
- 插入后的任务数量：4
- 未完成任务的排序结果：
  1. 学习MySQL建表（priority 3）
  2. 练习参数化SQL（priority 2）
  3. 临时任务（priority 1）
- 各优先级COUNT结果：priority 1 → 2条；priority 2 → 1条；priority 3 → 1条
- UPDATE结果：学习MySQL建表 的 completed 由 0 变为 1
- DELETE结果：临时任务 被删除，表中剩 3 条（id 1、2、3）
- 事务内的priority：3
- ROLLBACK后的priority：1

## 实际终端输出

### 1. 插入后查询全部（ORDER BY id）

```
+----+---------------------+-----------+----------+---------------------+
| id | title               | completed | priority | created_at          |
+----+---------------------+-----------+----------+---------------------+
|  1 | 学习MySQL建表       |         0 |        3 | 2026-09-29 11:13:08 |
|  2 | 复习HTTP状态码      |         1 |        1 | 2026-09-29 11:13:08 |
|  3 | 练习参数化SQL       |         0 |        2 | 2026-09-29 11:13:08 |
|  4 | 临时任务            |         0 |        1 | 2026-09-29 11:13:08 |
+----+---------------------+-----------+----------+---------------------+
```

### 2. 未完成任务（WHERE completed = FALSE，ORDER BY priority DESC, id ASC）

```
+----+--------------------+-----------+----------+
| id | title              | completed | priority |
+----+--------------------+-----------+----------+
|  1 | 学习MySQL建表      |         0 |        3 |
|  3 | 练习参数化SQL      |         0 |        2 |
|  4 | 临时任务           |         0 |        1 |
+----+--------------------+-----------+----------+
```

### 3. 各优先级统计（GROUP BY priority + COUNT(*)）

```
+----------+------------+
| priority | task_count |
+----------+------------+
|        1 |          2 |
|        2 |          1 |
|        3 |          1 |
+----------+------------+
```

### 4. UPDATE 并 DELETE 之后查询全部

```
+----+---------------------+-----------+----------+---------------------+
| id | title               | completed | priority | created_at          |
+----+---------------------+-----------+----------+---------------------+
|  1 | 学习MySQL建表       |         1 |        3 | 2026-09-29 11:13:08 |
|  2 | 复习HTTP状态码      |         1 |        1 | 2026-09-29 11:13:08 |
|  3 | 练习参数化SQL       |         0 |        2 | 2026-09-29 11:13:08 |
+----+---------------------+-----------+----------+---------------------+
```

（学习MySQL建表 completed 变成 1；临时任务 已被删除）

### 5. 事务内（START TRANSACTION 之后 UPDATE）

```
+---------------------+----------+
| title               | priority |
+---------------------+----------+
| 复习HTTP状态码      |        3 |
+---------------------+----------+
```

### 6. ROLLBACK 之后

```
+---------------------+----------+
| title               | priority |
+---------------------+----------+
| 复习HTTP状态码      |        1 |
+---------------------+----------+
```

（恢复了事务开始前的值）

### 7. SHOW CREATE TABLE tasks

```
CREATE TABLE `tasks` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `title` varchar(50) NOT NULL,
  `completed` tinyint(1) NOT NULL DEFAULT '0',
  `priority` tinyint unsigned NOT NULL DEFAULT '1',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  CONSTRAINT `chk_tasks_priority` CHECK ((`priority` between 1 and 3)),
  CONSTRAINT `chk_tasks_title` CHECK ((char_length(trim(`title`)) between 1 and 50))
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
```
