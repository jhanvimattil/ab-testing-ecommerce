# Homepage Banner A/B Testing Analysis

## Project Overview

This project analyzes an A/B test conducted on an e-commerce website homepage banner to determine which marketing strategy improves user conversions and revenue.

Two homepage banner variants were tested:

* **Variant A** → Discount-focused banner
* **Variant B** → Premium-quality messaging banner

The objective is to evaluate whether the new homepage banner significantly improves user engagement, conversions, and revenue generation.

---

# Business Problem

An e-commerce company wants to optimize its homepage experience to increase:

* Click-through rate (CTR)
* Add-to-cart rate
* Purchase conversion rate
* Revenue per visitor

The experiment compares two banner designs shown randomly to website visitors.

---

# Experiment Hypothesis

## Null Hypothesis (H0)

There is no statistically significant difference in conversion rates between Variant A and Variant B.

## Alternative Hypothesis (H1)

Variant B improves conversion rates compared to Variant A.

---

# Dataset Information

## Dataset Source

* Kaggle A/B Testing Dataset

## Dataset Columns

| Column Name      | Description                     |
| ---------------- | ------------------------------- |
| user_id          | Unique visitor ID               |
| timestamp        | Session timestamp               |
| variant          | A or B banner assignment        |
| device           | Mobile/Desktop/Tablet           |
| traffic_source   | Organic/Ads/Social/Email        |
| viewed_banner    | Whether user viewed banner      |
| clicked_banner   | Whether user clicked banner     |
| added_to_cart    | Whether user added item to cart |
| purchase         | Whether purchase occurred       |
| revenue          | Revenue generated from session  |
| session_duration | Session duration in seconds     |
| country          | User country                    |

# Tech Stack

## Programming & Analysis

* Python
* pandas
* numpy
* scipy
* statsmodels
* matplotlib

## Visualization

* Tableau

## Data Storage

* CSV

## Author- Jhanvi Mattil
