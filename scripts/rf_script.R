# DATA PREPPING

library(tidyverse)

accidents <- read.csv(file.choose())

roads <- read.csv(file.choose())

accidents_per_road <- accidents |>
  group_by(OBJECTID_2) |>
  summarize(accidents = n()) |>
  rename(OBJECTID = 'OBJECTID_2')

roads <- roads |>
  left_join(accidents_per_road, by = 'OBJECTID')

roads <- roads |>
  mutate(accidents = case_when(is.na(accidents)~0,
                               TRUE~accidents),
         avgviz = case_when(avgviz >1.0~1.0,
                            TRUE~avgviz),
         medcurve = case_when(medcurve >100000~100000,
                              TRUE~medcurve),
         mincurve = case_when(mincurve >100000~100000,
                              TRUE~mincurve),
         lqcurve = case_when(lqcurve >100000~100000,
                             TRUE~lqcurve)) |>
  filter(!is.na(avgviz))

unique_aotclass <- sort(unique(roads$AOTCLASS))
unique_aotclass

roads <- roads |>
  mutate(class = case_when(AOTCLASS == 1 ~ "High-Class Town Highway",
                           AOTCLASS == 2 ~ "High-Class Town Highway",
                           AOTCLASS == 3 ~ "Medium-Class Town Highway",
                           AOTCLASS == 4 ~ "Low-Class Town Highway",
                           AOTCLASS == 5 ~ "Low-Class Town Highway",
                           AOTCLASS == 6 ~ "Low-Class Town Highway",
                           AOTCLASS == 25 ~ "High-Class Town Highway",
                           AOTCLASS == 30 ~ "State Highway",
                           AOTCLASS == 35 ~ "State Highway",
                           AOTCLASS == 40 ~ "US Route",
                           AOTCLASS == 47 ~ "US Route",
                           AOTCLASS == 51 ~ "Interstate",
                           AOTCLASS == 52 ~ "Interstate",
                           AOTCLASS == 55 ~ "Interstate",
                           AOTCLASS == 56 ~ "Interstate",
                           AOTCLASS == 57 ~ "Interstate",
                           AOTCLASS == 60 ~ "Low-Class Town Highway"))

roads <- roads |>
  select(OBJECTID, SN, PRIMARYNAM, SURFACETYP, AOTCLASS, Shape_Leng, 
         minviz, avgviz, medcurve, mincurve, lqcurve, meanelev, medianelev, stdevelev, rangeelev,
         medslope, meanslope, maxslope, uqslope, accidents, class)

# EVALUATIONS

library(randomForest)

set.seed(1)

evals <- data.frame(matrix(NA, nrow = 200, ncol = 1000))

for (j in 1:10) {
  for (k in 1:20) {
    message(j,k)
    rf_iter <- randomForest(formula = accidents~ . -OBJECTID -SN -PRIMARYNAM -AOTCLASS,
                            data = roads,
                            ntree = 1000,
                            mtry = j,
                            importance = TRUE)
    evals[(j - 1) * 20 + k,] <- rf_iter$rsq
  }
}

evals <- evals |>
  mutate(mtry = as.integer(((row_number() - 1) / 20) + 1))

eval_sum <- evals |>
  group_by(mtry) |>
  summarize(across(where(is.numeric), \(x) mean(x, na.rm = TRUE)))

eval_sum_long <- eval_sum |>
  pivot_longer(
    cols = -mtry,
    names_to = "ntree",
    values_to = "mean_rsq") |>
  mutate(ntree = as.integer(gsub("X", "", ntree)))

eval_sum_long |>
  filter(mtry == 3) |>
  rename(`Average R-Squared Value` = "mean_rsq",
         `Number of Decision Trees` = "ntree") |>
  ggplot() +
  geom_point(aes(x = `Number of Decision Trees` , y = `Average R-Squared Value`)) +
  scale_x_log10()

eval_sum_long |>
  filter(ntree == 1000) |>
  rename(`Average R-Squared Value` = "mean_rsq") |>
  mutate(`Number of Variables Used per Tree` = as.factor(mtry)) |>
  ggplot() +
  geom_col(aes(x = `Number of Variables Used per Tree`, y = `Average R-Squared Value`))

# MODEL

set.seed(1)

rf <- randomForest(formula = accidents~ . -OBJECTID -SN -PRIMARYNAM -AOTCLASS,
                   data = roads,
                   ntree = 1000,
                   mtry = 3,
                   importance = TRUE,
                   keep.inbag = TRUE)

rf$importance

rf

predictions <- rf$predicted

road_predictions <- roads
road_predictions$predictions <- predictions

road_predictions <- road_predictions |>
  mutate(predictions = case_when(predictions < 0~0.0,
                                 TRUE~predictions))

## CREATING FIGURES

accidents <- accidents |>
  left_join(roads |> rename(OBJECTID_2 = "OBJECTID"))

roads$Source <- "All Roads"
accidents$Source <-"Accidents"

combined <- rbind(roads |> select(avgviz, lqcurve, meanelev, uqslope, class, Source),
                  accidents |> select(avgviz, lqcurve, meanelev, uqslope, class, Source))

desired_order <- c("Interstate",
                   "US Route",
                   "State Highway",
                   "High-Class Town Highway",
                   "Medium-Class Town Highway",
                   "Low-Class Town Highway")

combined |> 
  rename(`Average Visibility Score` = "avgviz",
         `Road Class` = "class") |>
  filter(!is.na(`Road Class`)) |>
  mutate(`Road Class` = factor(`Road Class`, levels = rev(desired_order))) |>
  ggplot() +
  geom_boxplot(aes(x = `Average Visibility Score`, y = `Road Class`, fill = Source), position = position_dodge(width = 0.8))

combined |> 
  rename(`Lower-Quartile Curve Radius (m)` = "lqcurve",
         `Road Class` = "class") |>
  filter(!is.na(`Road Class`)) |>
  mutate(`Road Class` = factor(`Road Class`, levels = rev(desired_order))) |>
  ggplot() +
  geom_boxplot(aes(x = `Lower-Quartile Curve Radius (m)`, y = `Road Class`, fill = Source), position = position_dodge(width = 0.8)) +
  scale_x_log10()

combined |> 
  rename(`Average Elevation (m)` = "meanelev",
         `Road Class` = "class") |>
  filter(!is.na(`Road Class`)) |>
  mutate(`Road Class` = factor(`Road Class`, levels = rev(desired_order))) |>
  ggplot() +
  geom_boxplot(aes(x = `Average Elevation (m)`, y = `Road Class`, fill = Source), position = position_dodge(width = 0.8))

combined |> 
  rename(`Upper-Quartile Slope` = "uqslope",
         `Road Class` = "class") |>
  filter(!is.na(`Road Class`)) |>
  mutate(`Road Class` = factor(`Road Class`, levels = rev(desired_order))) |>
  ggplot() +
  geom_boxplot(aes(x = `Upper-Quartile Slope`, y = `Road Class`, fill = Source), position = position_dodge(width = 0.8)) +
  scale_x_sqrt()

road_predictions |>
  rename(`Road Class` = "class") |>
  filter(!is.na(`Road Class`)) |>
  mutate(`Road Class` = factor(`Road Class`, levels = rev(desired_order)),
         `Predicted Single-Vehicle Accidents per km` = (predictions / Shape_Leng) * 1000) |>
  ggplot() +
  geom_boxplot(aes(x = `Predicted Single-Vehicle Accidents per km`, y = `Road Class`), outliers = FALSE)


