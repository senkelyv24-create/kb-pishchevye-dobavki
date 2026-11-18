-- Прямой вывод по правилам. Коды состава лежат во временной таблице ask(code).
-- :share_set = 0, если долю сахароспиртов не передали. :category — категория продукта.

-- @@additive
SELECT r.id, r.title, r.level, a.code AS code, r.body AS text
FROM rule r
JOIN additive a ON a.code IN (SELECT code FROM ask)
WHERE r.scope = 'additive'
  AND (r.need_status IS NULL OR a.status = r.need_status)
  AND (
        r.need_warning IS NULL
     OR EXISTS (
            SELECT 1 FROM additive_warning w
            WHERE w.additive_id = a.id AND w.warning = r.need_warning
        )
  )
  AND (r.need_code IS NULL OR a.code = r.need_code)
  AND (r.need_changed IS NULL OR a.changed_2024 = r.need_changed)
  AND (
        r.polyol_mode IS NULL
     OR (r.polyol_mode = 'unset' AND :share_set = 0)
     OR (r.polyol_mode = 'gt' AND :share_set = 1 AND :share > r.polyol_value)
     OR (r.polyol_mode = 'le' AND :share_set = 1 AND :share <= r.polyol_value)
  )
  AND (r.need_category IS NULL OR r.need_category = :category)
  AND NOT EXISTS (
        SELECT 1 FROM rule_category_exclude x
        WHERE x.rule_id = r.id AND x.category = :category
  );

-- @@composition
SELECT r.id, r.title, r.level, NULL AS code, r.body AS text
FROM rule r
WHERE r.scope = 'composition'
  AND (r.need_category IS NULL OR r.need_category = :category)
  AND EXISTS (SELECT 1 FROM rule_requires rr WHERE rr.rule_id = r.id)
  AND NOT EXISTS (
        SELECT 1 FROM rule_requires rr
        WHERE rr.rule_id = r.id
          AND rr.code NOT IN (SELECT code FROM ask)
  );
