import plotly.express as px
from shiny import App, render, ui, reactive
from shinywidgets import output_widget, render_plotly
import pandas as pd
import faicons as fa
import leafmap
import ipywidgets as widgets
from ipyleaflet import AwesomeIcon



# ------------------- Load the data ---------------------------------------------------------------------------------------------------------

df = pd.read_csv("merged_water_quality_weather.csv")
df["date"] = pd.to_datetime(df["date"])
df["date"] = pd.to_datetime(df["date"])
min_date = df["date"].min()
max_date = df["date"].max()

regions = df["region"].unique().tolist()
councils = df["council"].unique().tolist()


ICONS = {
    "site": fa.icon_svg("person-swimming", "solid"),
    "virus": fa.icon_svg("disease"),
    "check": fa.icon_svg("circle-check"),
}

# ------------------- Create the UI ----------------------------------------------------------------------------------------------------------

app_ui = ui.page_fluid(
    ui.navset_tab( 
        ui.nav_panel("Sydney Beach Water Quality Dashboard",  
            ui.layout_sidebar(
                ui.sidebar(
                            ui.div( ui.h3("Filters"),
                                    ui.input_date_range("daterange", "Select Date range", start=min_date, end=max_date, format="yyyy-mm-dd"),
                                    ui.br(),
                                    ui.input_checkbox_group(  
                                        "regions",  
                                        "Select Regions",  
                                        choices=regions,
                                        selected=[],  # Default selection of first three regions
                                    ),
                                    ui.br(),
                                    ui.input_selectize(
                                    "councils",
                                    "Select Councils",
                                    choices=councils,
                                    selected=[],
                                    multiple=True
                                                ),
                                    ui.br(),
                                    ui.download_button("download_data", "Download Data", class_="btn-primary", style="width: 100%;")
                            ), bg ="#035f86"),
                                ui.layout_column_wrap(
                                        ui.output_ui("total_beaches_box"),
                                        ui.output_ui("most_polluted_beach_box"),
                                        # ui.output_ui("most_frequently_polluted_beach_box"),
                                        ui.output_ui("cleanest_beach_box"),
                                    ),
                                    # Charts
                                ui.div(
                                    ui.layout_column_wrap(
                                        ui.card(
                                            ui.card_header('Which swim sites consistently have high enterococci levels?'),
                                            output_widget("high_enterococci_chart")
                                            ),
                                    
                                        ui.card(
                                            ui.card_header('How does water quality changes by season?'),
                                            output_widget("water_quality_by_season_chart")
                                            ),

                                        width = 1/2), class_="graph-section"),
                                        
                                        ui.card(
                                            ui.card_header('Water quality over the years'),
                                            output_widget("water_quality_over_years_chart")
                                        ),
                                        ui.card(
                                            ui.card_header('High Risk Areas'),
                                            ui.output_ui("high_risk_map")
                                        )

            )),
        ui.nav_panel("Data", "Page B content"),  
        ui.nav_panel("FAQ", "Page C content"),
        id="page" 
       )
    )


def server(input, output, session):
    import numpy as np
    
    # ------------------- Update Councils according to the selected regions ---------------------------------------------------------------------------
    @reactive.effect
    def update_councils():
        selected_regions = input.regions()

        if not selected_regions:
            ui.update_selectize("councils", choices=[], selected=[])
            return

        filtered_councils = df[df["region"].isin(selected_regions)]["council"].unique()
        filtered_councils = sorted(np.unique(filtered_councils))

        ui.update_selectize("councils", choices=filtered_councils, selected=[])

# ------------------- Update the first value box according to the selected date range, regions and councils ------------------------------------------------
    @reactive.calc      # filtered_df is a reactive expression that filters the DataFrame based on user input
    def filtered_df():
        selected_councils = input.councils()
        selected_regions = input.regions()
        start_date, end_date = input.daterange()
        start_date, end_date = pd.to_datetime(start_date), pd.to_datetime(end_date)

        if not selected_councils or not selected_regions or not start_date or not end_date:
            return df.iloc[0:0]  # return empty dataframe

        return df[
            (df["region"].isin(selected_regions)) &
            (df["council"].isin(selected_councils)) &
            (df["date"].between(start_date, end_date))
        ]
    
    #--------------------------------- ----------------------------------------------------------------------------------------------------------------------
    # -------------------------------------------------------------------------------------------------------------------------------------------------------
    # ------------------- ------------------------------- VALUE BOXES ---------------------------------------------------------------------------------------
    # -------------------------------------------------------------------------------------------------------------------------------------------------------
    # -------------------------------------------------------------------------------------------------------------------------------------------------------
    
    
    # ------------------- Render the total number of swim sites monitored as a reactive expression ------------------------------------------------------------------

    @reactive.calc
    def total_beaches():
        return len(filtered_df()["beach"].unique())
    
    # ------------------- render the total number of swim sites monitored as value box -----------------------------------------------------------------------------

    @render.ui
    def total_beaches_box():
        total = total_beaches()
        return ui.value_box(
            "Total Number of Swim Sites Monitored",
            f"{total:,} Swim Sites",
            showcase=ICONS["site"],
            theme="bg-gradient-orange-red",
        )
    
    # ------------------- reactive calculation for getting the most polluted beach (or most frequently polluted beach?)-------------------------------------------------------------------------------------------------
    @reactive.calc
    def most_polluted_beach():
        df_filtered = filtered_df()
        if df_filtered.empty:
            return "Please select"
        return df_filtered.groupby("beach")["enterococci"].mean().idxmax()
    
    # @reactive.calc
    # def most_frequently_polluted_beach():
    #     df_filtered = filtered_df()
    #     if df_filtered.empty:
    #         return "No data"

    #     threshold = 130

    #     polluted = df_filtered[df_filtered["enterococci"] > threshold]

    #     if polluted.empty:
    #         return "No polluted records"

    #     most_common = polluted["beach"].value_counts().idxmax()
    #     return most_common

    
    # ------------------- render the most polluted beach as a value box ----------------------------------------------------------------------------------------

    @render.ui
    def most_polluted_beach_box():
        return ui.value_box(
            "Most Polluted Beach",
            most_polluted_beach(),
            showcase=ICONS["virus"],
            theme="bg-gradient-green-blue",
            #showcase_layout="top right",
        )
    # ------------------- render the most frequently polluted beach as a value box ----------------------------------------------------------------------------------------
    # @render.ui
    # def most_frequently_polluted_beach_box():
    #     return ui.value_box(
    #         "Most Frequently Polluted Beach",
    #         most_frequently_polluted_beach(),
    #         showcase=ICONS["wallet"],
    #         theme="text-green",
    #         showcase_layout="top right",
    #         full_screen=True,
    #     )

# ------------------- reactive calc for getting the cleanest beach ------------------------------------------------------------
    @reactive.calc
    def cleanest_beach():
        df_filtered = filtered_df()
        if df_filtered.empty:
            return "Please select"
        return df_filtered.groupby("beach")["enterococci"].mean().idxmin()

# ------------------- render the cleanest beach as a value box ----------------------------------------------------------------------------------------

    @render.ui
    def cleanest_beach_box():
        return ui.value_box(
            "The Cleanest Beach",
            cleanest_beach(),
            showcase=ICONS["check"],
            theme="text-purple",
        )
# -------------------- reactive calculation for determining which swim sites consistently have high enterococci levels ------------------------------------------------

    @reactive.calc
    def high_enterococci_sites():
        df_filtered = filtered_df()
        if df_filtered.empty:
            return pd.DataFrame()

        # pollution threshold
        threshold = 130

        # Sort by count in descending order
        high_enterococci_df = df_filtered[df_filtered['enterococci'] > threshold].groupby('beach').size().reset_index(name='count')
        if high_enterococci_df.empty:
            return pd.DataFrame()
        return high_enterococci_df.sort_values(by='count', ascending=False)
    
    # ------------------- render the bar chart for high enterococci sites ----------------------------------------------------------------------------------------
    
    @render_plotly
    def high_enterococci_chart():
        df_high = high_enterococci_sites()
        if df_high.empty:
            return px.bar(title="No swim sites with high enterococci levels found.")

        fig = px.bar(
            df_high,
            x='beach',
            y='count',
            title='Swim Sites with High Enterococci Levels',
            labels={'beach': 'Swim Site', 'count': 'Number of High Enterococci Records'},
            color='count',
            color_continuous_scale=px.colors.sequential.Viridis
        )
        fig.update_layout(xaxis_title='Swim Site', yaxis_title='Number of High Enterococci Records')
        return fig
# -------------------- helper func for reactive calculation for determining how water quality changes by season ------------------------------------------------
    def month_to_season(month):
            if month in [12, 1, 2]:
                return 'Summer'
            elif month in [3, 4, 5]:
                return 'Autumn'
            elif month in [6, 7, 8]:
                return 'Winter'
            else:
                return 'Spring'

# --------------------  reactive calculation for determining how water quality changes by season ----------------------------------------------------------------
    @reactive.calc
    def water_quality_by_season():    
        df_filtered = filtered_df()
        if df_filtered.empty:
            return pd.DataFrame()

        # Extract season from date
        df_filtered = df_filtered.copy()
        df_filtered['month'] = df_filtered['date'].dt.month
        # Apply the function to create a new column for season
        df_filtered['season'] = df_filtered['month'].apply(month_to_season)

        # Group by season and beach, calculating mean enterococci, water temperature, and conductivity
        # Sort by enterococci levels in descending order        
        seasonal_quality = df_filtered.groupby(['season']).agg({'enterococci': 'mean',
                                                                      #'water_temperature': 'mean', 'conductivity': 'mean'
                                                                      }).reset_index()
        seasonal_quality = seasonal_quality.sort_values(by='enterococci', ascending=False)

        return seasonal_quality

# ------------------- render the bar chart for water quality by season ----------------------------------------------------------------------------------------
    @render_plotly
    def water_quality_by_season_chart():
        df_season = water_quality_by_season()
        if df_season.empty:
            return px.bar(title="No data available for the selected filters.")

        fig = px.bar(
            df_season,
            x='season',
            y='enterococci',
            title='Average Enterococci Levels by Season',
            labels={'season': 'Season', 'enterococci': 'Average Enterococci Level'},
            color='enterococci',
            color_continuous_scale=px.colors.sequential.Viridis
        )
        fig.update_layout(xaxis_title='Season', yaxis_title='Average Enterococci Level')
        return fig
    
# ------------------- water quality over the years --------------------------------------------------------------------------------------------------------
    @render_plotly
    def water_quality_over_years_chart():
        df_filtered = filtered_df()
        if df_filtered.empty:
            return px.bar(title="No data available for the selected filters.")

        # Extract year from date
        df_filtered['year'] = df_filtered['date'].dt.year

        # Group by year and calculate mean enterococci
        yearly_trends = df_filtered.groupby(['year', 'beach']).agg({
            'enterococci': 'mean',
        }).reset_index()
        yearly_trends = yearly_trends.sort_values(by=['year', 'enterococci'], ascending=[True, False])

        fig = px.line(
            yearly_trends,
            x='year',
            y='enterococci',
            color='beach',
            title='Average Enterococci Levels Over the Years',
            labels={'year': 'Year', 'enterococci': 'Average Enterococci Level'},
            
        )
        fig.update_layout(xaxis_title='Year', yaxis_title='Average Enterococci Level')
        return fig

# -------------------- add a map woth high risk areas ------------------------------------------------

    @reactive.calc
    def high_risk_map_html():
        df_filtered = filtered_df()
        if df_filtered.empty:
            return "<p>No data available.</p>"
        df_copy = df_filtered.copy()
        # Filter for high-risk swim sites (enterococci > 130)
        high_risk = df_copy[df_copy["enterococci"] > 130]

        if high_risk.empty:
            return "<p>No high-risk swim sites found.</p>"

        # Ensure lat/lon exist
        if not {'latitude', 'longitude'}.issubset(high_risk.columns):
            return "<p>Latitude and longitude columns are required to map locations.</p>"

        m = leafmap.Map(center=[-33.86, 151.20], zoom=10)  # Center on Sydney (adjust if needed)

        # Add high-risk sites to map
        for _, row in high_risk.iterrows():
            popup_html = widgets.HTML(value=f"{row['beach']}<br>Enterococci: {row['enterococci']}")
            icon = AwesomeIcon(name='exclamation-triangle', marker_color='red', icon_color='white')
            m.add_marker(
                location=(row["latitude"], row["longitude"]),
                popup=popup_html,
                icon=icon            
                )

        html_file = "map_high_risk.html"
        m.to_html(html_file)
        with open(html_file, "r", encoding="utf-8") as f:
            return f.read()

# -------------------- render the map with high risk areas ------------------------------------------------
    @render.ui
    def high_risk_map():
        return ui.HTML(high_risk_map_html())

app = App(app_ui, server)