import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import matplotlib.dates as mdates

data = {
    1:	92.466,
    2:	97.8185,
    3:	128.0531,
    4:	1370.3974,
    5:	1500.645,
    6:	1936.9788,
    7:	2182.1231,
    8:	2684.4023,
    9:	4378.6422,
    10:	7184.0842,
    11:	9542.8243,
    12:	11684.145,
    13:	13870.1536,
    14:	15412.7863,
    15:	15586.6636,
    16:	17025.2531,
    17:	18577.552,
    18:	19992.3569,
    19:	24217.8194,
    20:	24497.1143,
    21:	23121.0569,
    22:	26188.682,
    23:	27150.6165,
    24:	25278.8901,
    25:	25910.4771,
    26:	25530.265,
    27:	26137.7285,
    28:	27467.9568,
    29:	26957.5384,
    30:	26455.49,
    31:	25272.1638,
    32:	24894.4367,
    33:	25409.2323,
    34:	24615.399,
    35:	24168.9255,
    36:	24096.2864,
    37:	24350.8384,
    38:	24387.9522,
    39:	24167.3725,
    40:	24372.4174,
    41:	24192.1157,
    42:	23981.511,
    43:	24414.0461,
    44:	25021.9105,
    45:	25687.9018,
    46:	26281.6868,
    47:	26871.5767,
    48:	27147.0252,
    49:	27291.7197,
    50:	27663.8656,
    51:	27588.0913,
    52:	28081.6029,
    53:	28711.8066,
    54:	29628.8059,
    55:	30993.3604,
    56:	30399.8383,
    57:	31308.4316,
    58:	32155.1753,
    59:	32324.0122,
    60:	32240.7961
}


# Generate datetime labels from May 2020 to April 2025
start_date = datetime(2020, 5, 1)
dates = [start_date + timedelta(days=30 * i) for i in range(60)]  # Approximate months

# Extract values
values = [data[i + 1] for i in range(60)]

# Plot
plt.rcParams.update({'font.size': 20})
fig, ax = plt.subplots(figsize=(6, 6))
ax.plot(dates, values, marker='o')

# Set labels
ax.set_xlabel("time")
ax.set_ylabel("")
ax.grid(False)

# Format x-axis ticks
ax.xaxis.set_major_locator(mdates.YearLocator())
ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))  # e.g. "May 2020"
plt.xticks(rotation=45)

plt.tight_layout()
plt.show()
