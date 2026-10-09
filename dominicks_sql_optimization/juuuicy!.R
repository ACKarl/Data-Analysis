# 加载必要库
library(dplyr)
library(lubridate)
library(readr)

# -------------------------
# 读取数据
# -------------------------
setwd("Your/own/path")
bottled <- read_csv("wbjc.csv")
frozen  <- read_csv("wfrj.csv")


# -------------------------
# 3. 筛选有效行 (OK = 1)
# -------------------------
bottled <- bottled %>% filter(OK == 1)
frozen  <- frozen  %>% filter(OK == 1)

# -------------------------
# 3. 筛选有效行 (OK = 1)
# -------------------------
bottled <- bottled %>% filter(OK == 1)
frozen  <- frozen  %>% filter(OK == 1)

# -------------------------
# 4. 汇总数据（不再处理 SALE）
# -------------------------
bottled_summary <- bottled %>%
  group_by(UPC, WEEK) %>%
  summarise(
    Total_MOVE   = sum(MOVE, na.rm = TRUE),
    Total_QTY    = sum(QTY, na.rm = TRUE),
    Total_PROFIT = sum(PROFIT, na.rm = TRUE),
    Avg_PRICE    = mean(PRICE, na.rm = TRUE),
    .groups = "drop"
  ) %>%
  mutate(Category = "Bottled Juice")

frozen_summary <- frozen %>%
  group_by(UPC, WEEK) %>%
  summarise(
    Total_MOVE   = sum(MOVE, na.rm = TRUE),
    Total_QTY    = sum(QTY, na.rm = TRUE),
    Total_PROFIT = sum(PROFIT, na.rm = TRUE),
    Avg_PRICE    = mean(PRICE, na.rm = TRUE),
    .groups = "drop"
  ) %>%
  mutate(Category = "Frozen Juice")

# -------------------------
# 5. 合并两类果汁汇总表
# -------------------------
juices_summary <- bind_rows(bottled_summary, frozen_summary)

# -------------------------
# 6. 查看前几行
# -------------------------
head(juices_summary)

# -------------------------
# 7. 在 RStudio 查看完整表格
# -------------------------
View(juices_summary)

#-------------------------------------------------------------------------------------------

library(ggplot2)
install.packages("ggtern")
library(ggtern)
library(ggtern)

#------------------------------------------------------------------------------------------1
# 先选择一部分数据避免图太拥挤
sampled <- juices_summary %>% sample_n(min(5000, nrow(.)))

ggtern(sampled, aes(x = Total_MOVE, y = Total_PROFIT, z = Avg_PRICE, color = Category)) +
  geom_point(alpha = 0.7) +
  labs(
    title = "Ternary Plot of Juice Movement, Profit, and Price",
    x = "Total MOVE",
    y = "Total PROFIT",
    z = "Avg PRICE"
  ) +
  theme_minimal()

#------------------------------------------------------------------------------------------2
# 计算每周总销量（所有果汁类别）
total_per_week <- juices_summary %>%
  group_by(WEEK) %>%
  summarise(Total_MOVE_All = sum(Total_MOVE))

# 绘制柱状图 + 总销量折线
ggplot() +
  # 柱状图：Bottled vs Frozen
  geom_col(data = juices_summary,
           aes(x = WEEK, y = Total_MOVE, fill = Category),
           position = "dodge") +
  scale_fill_manual(values = c("Bottled Juice" = "blue", "Frozen Juice" = "red")) +
  # 折线：总销量趋势
  geom_line(data = total_per_week,
            aes(x = WEEK, y = Total_MOVE_All),
            color = "green", size = 1.2) +
  labs(title = "Weekly Juice Movement by Category with Total Trend",
       x = "Week",
       y = "Total MOVE") +
  theme_minimal()

#------------------------------------------------------------------------------------------3
library(dplyr)
library(ggplot2)

# -------------------------
# 1. 找出瓶装和冰冻果汁各自最热门的 UPC
# -------------------------
top_brands <- juices_summary %>%
  group_by(Category, UPC) %>%
  summarise(Total_MOVE_All = sum(Total_MOVE, na.rm = TRUE), .groups = "drop") %>%
  arrange(Category, desc(Total_MOVE_All))

# 取每类果汁销量最高的 UPC
bottled_upc <- top_brands %>% filter(Category == "Bottled Juice") %>% slice(1) %>% pull(UPC)
frozen_upc  <- top_brands %>% filter(Category == "Frozen Juice")  %>% slice(1) %>% pull(UPC)

# -------------------------
# 2. 给价格分层 (Price Tier)
# -------------------------
juices_summary <- juices_summary %>%
  mutate(
    Price_Tier = case_when(
      Avg_PRICE <= 1 ~ "Low",
      Avg_PRICE <= 1.25 ~ "Medium",
      Avg_PRICE <= 1.5 ~ "High",
      TRUE       ~ "Premium"
    ),
    Price_Tier = factor(Price_Tier, levels = c("Low", "Medium", "High", "Premium"), ordered = TRUE)
  )
  

# -------------------------
# 3. 筛选两个热门品牌的数据
# -------------------------
box_data <- juices_summary %>%
  filter((Category == "Bottled Juice" & UPC == bottled_upc) |
           (Category == "Frozen Juice"  & UPC == frozen_upc))

# -------------------------
# 4. 绘制箱型图
# -------------------------
ggplot(box_data, aes(x = Price_Tier, y = Total_MOVE, fill = Category)) +
  geom_boxplot(alpha = 0.7) +
  scale_fill_manual(values = c("Bottled Juice" = "green", "Frozen Juice" = "red")) +
  labs(title = "Juice Movement by Price Tier for Two Popular Brands",
       x = "Price Tier",
       y = "Total MOVE") +
  theme_minimal()

# -------------------------
# 5. 保存图
# -------------------------
ggsave("brand_price_boxplot.png", width = 8, height = 5)

#------------------------------------------------------------------------------------4

juices_price_tier <- juices %>%
  mutate(
    Price_Tier = case_when(
      PRICE == 1        ~ "Low",
      PRICE == 1.25     ~ "Medium",
      PRICE == 1.5      ~ "High",
      PRICE >  1.5      ~ "Premium",
      TRUE              ~ NA_character_
    ),
    # 将 Price_Tier 转成有序因子以保证顺序
    Price_Tier = factor(Price_Tier, levels = c("Low", "Medium", "High", "Premium"), ordered = TRUE)
  ) %>%
  filter(!is.na(Price_Tier))  # 丢掉不在这些层次的行

# -------------------------
# 3. 筛选两个热门 UPC 并汇总每个价格层的 MOVE
# -------------------------
plot_data <- juices_price_tier %>%
  filter((Category == "Bottled Juice" & UPC == bottled_upc) |
         (Category == "Frozen Juice"  & UPC == frozen_upc)) %>%
  group_by(Category, Price_Tier) %>%
  summarise(Total_MOVE = sum(MOVE, na.rm = TRUE), .groups = "drop") %>%
  # 为了做蝴蝶图，把 Frozen 的值取负（让它向左），Bottled 保持正（向右）
  mutate(
    Value = ifelse(Category == "Frozen Juice", -Total_MOVE, Total_MOVE),
    # 便于在条上标注绝对值和控制标签位置
    Label = formatC(abs(Total_MOVE), format="d", big.mark=","),
    hjust = ifelse(Value < 0, 1.1, -0.1)  # 文字位置：左边靠内，右边靠外；coord_flip 后效果良好
  )

# 如果某些 Price_Tier 在某一个 Category 没记录，补 0（保证两个类别每层都有一个条）
all_tiers <- data.frame(Price_Tier = factor(c("Low", "Medium", "High", "Premium"),
                                            levels = c("Low", "Medium", "High", "Premium"), ordered = TRUE))
complete_data <- expand.grid(Category = c("Bottled Juice","Frozen Juice"), Price_Tier = all_tiers$Price_Tier,
                             stringsAsFactors = FALSE) %>%
  left_join(plot_data, by = c("Category","Price_Tier")) %>%
  mutate(
    Total_MOVE = ifelse(is.na(Total_MOVE), 0, Total_MOVE),
    Value = ifelse(Category == "Frozen Juice", -Total_MOVE, Total_MOVE),
    Label = formatC(abs(Total_MOVE), format="d", big.mark=","),
    hjust = ifelse(Value < 0, 1.1, -0.1)
  )

# -------------------------
# 4. 绘制蝴蝶图
# -------------------------
p <- ggplot(complete_data, aes(x = Price_Tier, y = Value, fill = Category)) +
  geom_col(width = 0.6) +
  coord_flip() +
  # 显示绝对值刻度（用自定义标签把负数显示为正）
  scale_y_continuous(labels = function(x) formatC(abs(x), format="d", big.mark=",")) +
  scale_fill_manual(values = c("Bottled Juice" = "green", "Frozen Juice" = "red")) +
  geom_text(aes(label = Label, hjust = hjust), color = "black", size = 3.2) +
  labs(title = "Butterfly chart: MOVE by Price Tier for Top Bottled & Frozen UPCs",
       subtitle = paste0("Bottled UPC: ", bottled_upc, " (green)  —  Frozen UPC: ", frozen_upc, " (red)"),
       x = "Price Tier",
       y = "Total MOVE (absolute)", 
       fill = "Category") +
  theme_minimal(base_size = 12) +
  theme(legend.position = "bottom")

print(p)

# 保存为 PNG
ggsave("butterfly_top_brands.png", p, width = 8, height = 4)

#----------------------------------------------------------------------------------------5

# 创建黑白风格的泡沫图
ggplot(bubble_data, aes(x = WEEK, y = price_level, size = Total_Sales)) +
  geom_point(alpha = 0.7, color = "black") +
  scale_size_continuous(range = c(2, 10)) +
  labs(
    title = "Sales by Week and Price Level",
    x = "Week",
    y = "Price Level",
    size = "Sales Volume"
  ) +
  theme_minimal() +
  theme(
    plot.title = element_text(hjust = 0.5, face = "bold"),
    panel.grid.major = element_line(color = "grey90"),
    panel.background = element_rect(fill = "white"),
    legend.position = "bottom"
  ) +
  scale_x_continuous(breaks = seq(0, 400, by = 50)) +
  facet_wrap(~Category, ncol = 1)  # 按类别分面显示

#-----------------------------------------------------------------------------------------6
library(dplyr)
library(ggplot2)

# 合并并清洗（去掉 NA）
juices <- bind_rows(
  bottled %>% mutate(Category = "Bottled"),
  frozen %>% mutate(Category = "Frozen")
) %>%
  filter(!is.na(PRICE), !is.na(PROFIT), !is.na(MOVE), PRICE > 0, MOVE > 0)

# 添加价格等级
juices <- juices %>%
  mutate(price_level = case_when(
    PRICE > 1 & PRICE <= 1.25 ~ "low",
    PRICE > 1.25 & PRICE <= 1.5 ~ "medium",
    PRICE > 1.5 & PRICE <= 2 ~ "high",
    PRICE > 2 ~ "premium",
    TRUE ~ NA_character_
    
  ),
  PRICE = ifelse(PRICE > 1.5, 2, PRICE)
  ) %>%
  filter(!is.na(price_level))   # 去掉没有价格等级的行

# 按价格等级 + 价格聚合
bubble_data <- juices %>%
  group_by(price_level, PRICE) %>%
  summarise(
    avg_profit = mean(PROFIT, na.rm = TRUE),
    total_sales = sum(MOVE, na.rm = TRUE),
    .groups = "drop"
  )

# 画气泡图
ggplot(bubble_data, aes(x = PRICE, y = avg_profit, size = total_sales, color = price_level)) +
  geom_point(alpha = 0.7) +
  scale_size_area(max_size = 15) +
  scale_color_manual(values = c("low" = "blue", "medium" = "green", "high" = "orange", "premium" = "red")) +
  labs(
    title = "Bubble Chart: Price vs Profit (Aggregated by Price Level)",
    x = "Price",
    y = "Average Profit",
    size = "Total Sales",
    color = "Price Level"
  ) +
  theme_minimal()


