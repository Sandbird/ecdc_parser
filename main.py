import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import random
from tkinter import *
from tkinter import ttk
import requests
import os


# URL of the CSV files
# Delete the .csv files if they exist locally to re-download the latest data
surl = 'https://raw.githubusercontent.com/EU-ECDC/Respiratory_viruses_weekly_data/main/data/nonSentinelSeverity.csv'
surlfile = 'nonSentinelSeverity.csv'

vurl = 'https://raw.githubusercontent.com/EU-ECDC/Respiratory_viruses_weekly_data/main/data/variants.csv'
vurlfile = 'variants.csv'


# Download the CSV file if it doesn't exist locally
if not os.path.exists(surlfile):
    response = requests.get(surl)
    with open(surlfile, 'wb') as f:
        f.write(response.content)

# Download the CSV file if it doesn't exist locally
if not os.path.exists(vurlfile):
    response = requests.get(vurl)
    with open(vurlfile, 'wb') as f:
        f.write(response.content)   


# Function to read available countries from CSV files
def get_available_countries():
    variants_df = pd.read_csv(vurlfile)
    severity_df = pd.read_csv(surlfile)
    countries_variants = variants_df['countryname'].unique()
    countries_severity = severity_df['countryname'].unique()
    countries = set(countries_variants).union(set(countries_severity))
    return sorted(list(countries))

def is_bright(color, threshold=0.7):
    # Calculate the luminance of the color
    luminance = 0.2126 * color[0] + 0.7152 * color[1] + 0.0722 * color[2]
    # Check if the luminance is above the threshold
    return luminance > threshold

def color_distance(color1, color2):
    # Calculate Euclidean distance between two colors in RGB space
    return np.linalg.norm(np.array(color1) - np.array(color2))

def random_color_generator(num_colors, min_distance=0.2, seed=None):
    if seed is not None:
        random.seed(seed)
    colors = []
    available_colors = list(mcolors.CSS4_COLORS.keys())  # Use keys to get color names directly
    while len(colors) < num_colors:
        color_name = random.choice(available_colors)
        color_rgb = mcolors.to_rgb(color_name)
        if not is_bright(color_rgb):
            # Check distance from other colors
            if all(color_distance(color_rgb, mcolors.to_rgb(c)) > min_distance for c in colors):
                colors.append(color_name)
    return colors


# Function to update the plot based on selected country
def update_plot():
    country = country_variable.get()
    update_plot_with_country(country)

# Function to update the plot with a given country
def update_plot_with_country(country):
    # Read variants data from CSV
    
    variants_df = pd.read_csv(vurlfile)
    variants_df = variants_df[(variants_df['countryname'] == country) & 
                              (variants_df['pathogen'] == 'SARS-CoV-2') &
                              (variants_df['indicator'] == 'proportion')]
    variants_df = variants_df.groupby(['yearweek', 'variant']).agg({'value': 'sum'}).reset_index()
    variants = variants_df.pivot(index='yearweek', columns='variant', values='value').fillna(0)
    variants.index = pd.to_datetime(variants.index + '-1', format='%G-W%V-%u').map(lambda x: x.strftime('%Y-%m-%d'))
    variants = variants.loc['2020-08-20':]

    # Get the number of random colors using a seed
    num_colors = len(variants.columns)
    variant_colors = random_color_generator(num_colors, seed=1123)

    # Read severity data from CSV    
    severity_df = pd.read_csv(surlfile)
    severity_df = severity_df[(severity_df['countryname'] == country) &
                              (severity_df['pathogen'] == 'SARS-CoV-2') &
                              (severity_df['age'] == 'total') &
                              (severity_df['indicator'].isin(['hospitaladmissions', 'ICUadmissions', 'deaths']))]
    severity_df['date'] = pd.to_datetime(severity_df['yearweek'] + '-1', format='%G-W%V-%u').map(lambda x: x.strftime('%Y-%m-%d'))
    severity_df.reset_index(drop=True, inplace=True)
    severity_pivot = severity_df.pivot(index='date', columns='indicator', values='value').fillna(0)
    severity_pivot = severity_pivot.loc['2020-08-20':]
    variants = variants.reindex(severity_pivot.index)

    # Plotting...
    fig, ax1 = plt.subplots(figsize=(16, 10))
    cases_bar = ax1.bar(np.arange(len(severity_pivot.index)), severity_pivot['hospitaladmissions'], color='#C5DFB9', alpha=0.5, label='Hosp. Admissions')
    icu_bar = ax1.bar(np.arange(len(severity_pivot.index)), severity_pivot['ICUadmissions'], color='#548135', alpha=0.5, label='ICU', bottom=severity_pivot['deaths'])
    deaths_bar = ax1.bar(np.arange(len(severity_pivot.index)), severity_pivot['deaths'], color='black', alpha=0.5, label='Deaths')
    
    ax2 = ax1.twinx()
    for i, variant in enumerate(variants.columns):
        line = ax2.plot(variants.index, variants[variant], marker='', linestyle='-', color=variant_colors[i], label=f'{variant}', linewidth=2.5)
        max_value = variants[variant].max()
        if max_value > 40:
            max_index = variants[variants[variant] == max_value].index[0]
            ax2.text(max_index, max_value, f'{variant}', color=variant_colors[i], ha='center', va='bottom', fontsize=10)
    ax1.set_ylabel('Severity')
    ax2.set_ylabel('Percentage of variants (%)')
    ax2.tick_params(axis='y')
    ax1.set_ylim(bottom=0)
    ax2.set_ylim(bottom=0)
    ax1.set_xticks(np.arange(0, len(severity_pivot.index), 2))
    ax1.set_xticklabels(severity_pivot.index[::2], rotation='vertical', fontsize=8)
    dates = pd.to_datetime(severity_pivot.index)
    ax1.set_xlim(0, len(dates) - 1)
    ax1.grid(axis='y', alpha=0.3, zorder=0)
    variant_patches = []
    for i, (variant, color) in enumerate(zip(variants.columns, variant_colors)):
        variant_patches.append(plt.Rectangle((0, 0), 1, 1, color=color, label=variant))
    plt.title(f'{country} - COVID Hosp., ICU patients, Deaths (L) % Variant (R)', loc='center', fontsize=16, fontname='DejaVu Sans', alpha=0.5)
    legend_handles = [cases_bar, icu_bar, deaths_bar] + variant_patches

    # Split variant patches into rows with a maximum of 8 items per row
    max_per_row =9
    num_cols = min(max_per_row, len(variant_patches))
    # Create the legend with the appropriate number of columns
    legend = plt.legend(handles=legend_handles, loc='lower center', bbox_to_anchor=(0.5, -0.2), ncol=num_cols, frameon=False)
    plt.text(1.0, -0.2, 'ECDC data', ha='right', va='bottom', fontsize=12, color='gray', transform=ax1.transAxes)
    legend.get_frame().set_linewidth(0.0)
    plt.subplots_adjust(bottom=0.1)
    plt.tight_layout()
    plt.show()

# Initialize Tkinter window
root = Tk()
root.title("COVID-19 Analysis")

# Create a dropdown list of countries
country_variable = StringVar(root)
country_variable.set("Select Country")
countries = get_available_countries()
country_variable.set("Greece")  # Set default country here
country_dropdown = ttk.Combobox(root, textvariable=country_variable, values=countries)
country_dropdown.grid(row=0, column=0, padx=10, pady=10)

# Button to update the plot
update_button = Button(root, text="Create Plot", command=update_plot)
update_button.grid(row=0, column=1, padx=10, pady=10)

# Initialize plot with the default country
update_plot_with_country(country_variable.get())

# Run the main loop
root.mainloop()
