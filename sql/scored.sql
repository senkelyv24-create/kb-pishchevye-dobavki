-- Ранжирование одной добавки. Пустой запрос даёт каталог (вес 1).
-- Иначе первое сработавшее условие задаёт вес и причину, как в прямом сопоставлении.
SELECT
    a.id,
    a.code,
    a.slug,
    a.name_ru,
    a.name_en,
    a.group_code,
    a.status,
    a.origin,
    a.summary,
    a.eu_note,
    a.changed_2024,
    CASE
        WHEN :needle = '' THEN 1
        WHEN :compact IN (
            lower(a.code),
            replace(lower(a.code), '-', ''),
            replace(lower(a.code), 'e', '')
        ) THEN 100
        WHEN :compact LIKE 'e%' AND lower(a.code) LIKE :compact || '%' THEN 70
        WHEN EXISTS (
            SELECT 1 FROM additive_alias al
            WHERE al.additive_id = a.id AND al.alias_norm = :needle
        ) THEN 90
        WHEN :needle IN (a.name_ru_norm, a.name_en_norm) THEN 85
        WHEN instr(a.name_ru_norm, :needle) > 0 OR instr(a.name_en_norm, :needle) > 0 THEN 55
        WHEN EXISTS (
            SELECT 1 FROM additive_alias al
            WHERE al.additive_id = a.id
              AND (
                    instr(al.alias_norm, :needle) > 0
                 OR instr(:needle, al.alias_norm) > 0
              )
        ) THEN 50
        WHEN EXISTS (
            SELECT 1 FROM additive_function f
            WHERE f.additive_id = a.id AND instr(f.name_norm, :needle) > 0
        ) THEN 30
        WHEN instr(a.summary_norm, :needle) > 0 THEN 15
        ELSE 0
    END AS score,
    CASE
        WHEN :needle = '' THEN 'раздел каталога'
        WHEN :compact IN (
            lower(a.code),
            replace(lower(a.code), '-', ''),
            replace(lower(a.code), 'e', '')
        ) THEN 'точный индекс'
        WHEN :compact LIKE 'e%' AND lower(a.code) LIKE :compact || '%' THEN 'индекс начинается с запроса'
        WHEN EXISTS (
            SELECT 1 FROM additive_alias al
            WHERE al.additive_id = a.id AND al.alias_norm = :needle
        ) THEN 'совпало дополнительное имя'
        WHEN :needle IN (a.name_ru_norm, a.name_en_norm) THEN 'совпало наименование'
        WHEN instr(a.name_ru_norm, :needle) > 0 OR instr(a.name_en_norm, :needle) > 0 THEN 'часть наименования'
        WHEN EXISTS (
            SELECT 1 FROM additive_alias al
            WHERE al.additive_id = a.id
              AND (
                    instr(al.alias_norm, :needle) > 0
                 OR instr(:needle, al.alias_norm) > 0
              )
        ) THEN 'близкое имя'
        WHEN EXISTS (
            SELECT 1 FROM additive_function f
            WHERE f.additive_id = a.id AND instr(f.name_norm, :needle) > 0
        ) THEN 'технологическая функция'
        WHEN instr(a.summary_norm, :needle) > 0 THEN 'слово из описания'
        ELSE ''
    END AS reason
FROM additive a
WHERE (:group_code = '' OR a.group_code = :group_code)
  AND (
        :status = ''
     OR (:status = 'excluded' AND a.status = 'excluded')
     OR (:status = 'allowed' AND a.status = 'allowed')
     OR (:status = 'warning' AND EXISTS (
            SELECT 1 FROM additive_warning w WHERE w.additive_id = a.id
        ))
     OR (:status = 'changed' AND a.changed_2024 = 1)
  )
