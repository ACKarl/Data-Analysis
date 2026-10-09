# -------------------------
# 0. 加载必要库
# -------------------------
library(dplyr)
library(readr)
library(ggtern)
library(viridis)

# -------------------------
# 1. 读取 CSV 数据
# -------------------------
setwd("Your/own/path")
bottled <- read_csv("wbjc.csv")
frozen  <- read_csv("wfrj.csv")

# 转换数值列
num_cols <- c("MOVE","QTY","PROFIT","PRICE")
bottled[num_cols] <- lapply(bottled[num_cols], as.numeric)
frozen[num_cols]  <- lapply(frozen[num_cols], as.numeric)

# 合并数据
juices <- bind_rows(
  bottled %>% mutate(Category="Bottled Juice"),
  frozen  %>% mutate(Category="Frozen Juice")
)

# 汇总
juices_summary <- juices %>%
  group_by(Category, UPC, WEEK) %>%
  summarise(
    Total_MOVE   = sum(MOVE, na.rm=TRUE),
    Total_QTY    = sum(QTY, na.rm=TRUE),
    Total_PROFIT = sum(PROFIT, na.rm=TRUE),
    Avg_PRICE    = mean(PRICE[PRICE > 0], na.rm=TRUE),
    .groups="drop"
  ) %>%
  filter(Avg_PRICE > 0)

# 随机抽样避免绘图过慢
set.seed(123)
sampled <- juices_summary %>% sample_n(min(5000, nrow(.)))

# 三元密度图
ggtern(sampled, aes(x = Total_MOVE, y = Total_PROFIT, z = Avg_PRICE)) +
  stat_density_tern(geom="polygon", alpha=0.8, bdl=0.01, aes(fill=..level..)) +
  scale_fill_viridis_c(option="plasma") +
  labs(title="Ternary Density Plot of Juice Movement, Profit, and Price",
       x="Total MOVE", y="Total PROFIT", z="Avg PRICE", fill="Density") +
  theme_minimal()
