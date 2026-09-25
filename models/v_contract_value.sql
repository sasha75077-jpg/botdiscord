CREATE VIEW v_contract_value AS
WITH base AS (
  SELECT
    c.*,
    (
      CASE c.contract_type
        WHEN 'активация' THEN COALESCE(c.price, 0)
        WHEN 'дары-моря' THEN 0
        WHEN 'ателье' THEN
          COALESCE(c.atelier_total_uniforms, 0) *
          COALESCE((SELECT p.price FROM prices p WHERE p.item_key = 'atelier.uniform'), 0)
        WHEN 'металлургия-сдача' THEN
          CASE c.ore_type
            WHEN 'Железная руда'   THEN COALESCE((SELECT p.price FROM prices p WHERE p.item_key = 'ore.delivery.iron'), 0)
            WHEN 'Серебряная руда' THEN COALESCE((SELECT p.price FROM prices p WHERE p.item_key = 'ore.delivery.silver'), 0)
            WHEN 'Медная руда'     THEN COALESCE((SELECT p.price FROM prices p WHERE p.item_key = 'ore.delivery.copper'), 0)
            WHEN 'Оловянная руда'  THEN COALESCE((SELECT p.price FROM prices p WHERE p.item_key = 'ore.delivery.tin'), 0)
            WHEN 'Золотая руда'    THEN COALESCE((SELECT p.price FROM prices p WHERE p.item_key = 'ore.delivery.gold'), 0)
            ELSE 0
          END
        WHEN 'металлургия-добыча' THEN
          COALESCE(c.m_iron, 0)   * COALESCE((SELECT p.price FROM prices p WHERE p.item_key = 'ore_unit:iron'), 0) +
          COALESCE(c.m_silver, 0) * COALESCE((SELECT p.price FROM prices p WHERE p.item_key = 'ore_unit:silver'), 0) +
          COALESCE(c.m_copper, 0) * COALESCE((SELECT p.price FROM prices p WHERE p.item_key = 'ore_unit:copper'), 0) +
          COALESCE(c.m_tin, 0)    * COALESCE((SELECT p.price FROM prices p WHERE p.item_key = 'ore_unit:tin'), 0) +
          COALESCE(c.m_gold, 0)   * COALESCE((SELECT p.price FROM prices p WHERE p.item_key = 'ore_unit:gold'), 0)
        WHEN 'товары' THEN
          (CASE WHEN UPPER(COALESCE(c.goods_delivery,'')) IN ('YES','TRUE','1') THEN
              COALESCE((SELECT p.price FROM prices p WHERE p.item_key = 'goods.delivery'), 0)
            ELSE 0 END) +
          (CASE WHEN UPPER(COALESCE(c.goods_loading,'')) IN ('YES','TRUE','1') THEN
              COALESCE((SELECT p.price FROM prices p WHERE p.item_key = 'goods.loading'), 0)
            ELSE 0 END)
        WHEN 'агитации-маркетплейс' THEN
          COALESCE(c.marketplace_links_count, 0) *
          COALESCE((SELECT p.price FROM prices p WHERE p.item_key = 'agit:marketplace_link'), 0)
        WHEN 'агитации-wn' THEN
          CASE
            WHEN TRIM(COALESCE(c.wn_category, '')) = 'Зеленка(чат)' THEN
              COALESCE(c.wn_screenshots_count, 0) *
              COALESCE((SELECT p.price FROM prices p WHERE p.item_key = 'agit:wn_green'), 0)
            WHEN TRIM(COALESCE(c.wn_category, '')) = 'Уведомление' THEN
              COALESCE(c.wn_screenshots_count, 0) *
              COALESCE((SELECT p.price FROM prices p WHERE p.item_key = 'agit:wn_notice'), 0)
            ELSE 0
          END
        WHEN 'тюнинг' THEN
          COALESCE((SELECT p.price FROM prices p WHERE p.item_key = 'tuning:with_screenshot'), 0)
        WHEN 'курьер-еды' THEN
          COALESCE((SELECT p.price FROM prices p WHERE p.item_key = 'courier:delivery'), 0)
        ELSE 0
      END
    ) AS base_price
  FROM "contracts" c
  WHERE c.confirm_status = 'APPROVED'
    AND COALESCE(c.voided, 0) = 0
)
SELECT
  base.*,
  CASE
    WHEN base.contract_type IN ('товары', 'металлургия-сдача')
    THEN COALESCE(rk.sort_order, 0) * 1000
    ELSE 0
  END AS rank_bonus,
  CASE
    WHEN base.contract_type IN ('тюнинг', 'курьер-еды')
    THEN COALESCE(rk.sort_order, 0) * 100
    ELSE 0
  END AS tuning_rank_bonus,
  (
    base.base_price
    + CASE
        WHEN base.contract_type IN ('товары', 'металлургия-сдача')
        THEN COALESCE(rk.sort_order, 0) * 1000
        ELSE 0
      END
    + CASE
        WHEN base.contract_type IN ('тюнинг', 'курьер-еды')
        THEN COALESCE(rk.sort_order, 0) * 100
        ELSE 0
      END
  ) AS calc_price
FROM base
LEFT JOIN "users" u ON u.discord_id = base.discord_id AND COALESCE(u.guild_id, '') = COALESCE(base.guild_id, '')
LEFT JOIN "ranks" rk ON rk.id = u.current_rank_id
