import plotly.express as px
from shiny import App, render, ui, reactive
from shinywidgets import output_widget, render_plotly, render_widget
import pandas as pd
import faicons as fa
import leafmap
from ipyleaflet import Map, CircleMarker, LayerGroup
import ipywidgets as widgets
from ipywidgets import HTML  
from ipyleaflet import AwesomeIcon
import chatlas
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "querychat", "pkg-py"))
from dotenv import load_dotenv
import querychat as qc

# ------------------- Load the data ---------------------------------------------------------------------------------------------------------

df = pd.read_csv("merged_water_quality_weather.csv")
df["date"] = pd.to_datetime(df["date"])
df["date"] = pd.to_datetime(df["date"])
min_date = df["date"].min()
max_date = df["date"].max()

# ----------------------default values to reset filters -----------------------------------------------------------------------------------------

DEFAULT_DATE_RANGE = (min_date, max_date)
DEFAULT_REGIONS = []        
DEFAULT_COUNCILS = []


regions = df["region"].unique().tolist()
councils = df["council"].unique().tolist()

ICONS = {
    "site": fa.icon_svg("person-swimming", "solid"),
    "virus": fa.icon_svg("disease"),
    "check": fa.icon_svg("circle-check"),
}
# ----------------------------  define the LLM model ---------------------------------------------------------------------------------

def use_anthropic_models(system_prompt: str) -> chatlas.Chat:

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set in the environment.")

    return chatlas.ChatAnthropic(
        model="claude-3-7-sonnet-latest",
        system_prompt=system_prompt,
        api_key=api_key 
    )



chat_config = qc.init(df, "df", create_chat_callback=use_anthropic_models)

# ------------------- Create the UI ----------------------------------------------------------------------------------------------------------

app_ui = ui.page_fluid(

    ui.tags.style("""
                    /* Make sidebar toggle arrow thicker and white */
                    .sidebar-toggle {
                        color: white !important;
                        font-weight: bold;
                        font-size: 20px;
                        border: 2px solid white !important;
                    }
                    .value-box {
                        min-height: 140px;
                        display: flex;
                        flex-direction: column;
                        justify-content: center;
                        text-align: center;
                    }

                    .value-box-showcase {
                        font-size: 1em;
                    }

                    .value-box-value {
                        font-size: 0.5em;
                        white-space: nowrap;
                        overflow: hidden;
                        text-overflow: ellipsis;
                    }

                    .value-box-title {
                        font-size: 1.5em;
                    }
                    """),
    ui.navset_tab (
        ui.nav_panel("Sydney Beach Water Quality Dashboard",  
            ui.layout_sidebar(
                ui.sidebar(
                            ui.div( ui.h3("Filters"),
                                    ui.input_date_range("daterange", "Select Date range", start="2020-04-28", end=max_date, format="yyyy-mm-dd", width= "100%"),
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
                                    ui.download_button("download_data", "Download Data", class_="btn-primary", style="width: 100%; margin-bottom: 10px;"),
                                    ui.br(),
                                    ui.br(),
                                    ui.input_action_button("reset", "Reset filter", class_="btn-primary", style="width: 100%;"),
                                    open="desktop",
                            ), bg ="#035f86", style="color: white;"),
                                ui.row(
                                        ui.column(4, ui.output_ui("total_beaches_box")),
                                        ui.column(4, ui.output_ui("most_polluted_beach_box")),
                                        # ui.output_ui("most_frequently_polluted_beach_box"),
                                        ui.column(4, ui.output_ui("cleanest_beach_box")),
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
                                            ui.card_header("Map of Beaches Colored by Enterococci Levels"),
                                            output_widget("beach_map", height="500px")
                                        ),


            )),
        ui.nav_panel(
            "FAQ", 
            ui.accordion(
                    ui.accordion_panel(
                        "Which beaches are most frequently polluted?",
                        ui.p("This chart shows the beaches with the highest number of exceedances (Enterococci > 130 CFU/100mL)."),
                        ui.layout_column_wrap(
                        ui.card(output_widget("faq_high_risk_chart")),
                        ui.card(ui.output_data_frame("faq_high_risk_df"))
                    )),
                    ui.accordion_panel(
                        "How does water quality vary seasonally?",
                        ui.p("Seasonal variations may influence pollution levels due to rainfall or water temperature."),
                        ui.layout_column_wrap(
                        ui.card(output_widget("faq_seasonal_variation_chart")),
                        ui.card(ui.output_data_frame("faq_seasonal_variation_df"))
                    )),
                    ui.accordion_panel(
                        "What data is used in this dashboard?",
                        ui.p("This dashboard combines water quality measurements, weather conditions, and geographical data from public sources such as the NSW EPA.")
                    ),
                    ui.accordion_panel(
                        "How are high-risk areas identified?",
                        ui.p("High-risk beaches are those with repeated high Enterococci levels, based on thresholds from health guidelines."),
                        ui.output_ui("faq_high_risk_map")
                    ),
                    open=False,
                ),            
            ),  
        ui.nav_panel(
            "Query Chat",
                ui.layout_sidebar(
                    ui.sidebar(
                        qc.ui("chat"),
                        width=350
                    ),
                    ui.layout_column_wrap(    
                        ui.card(
                            ui.card_header("Live Filtered Data"),
                            ui.output_data_frame("chat_filtered_df")
                        ),
                        width=1)
                )),
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
        if total == 0:
            return ui.value_box(
            "Total Swim Sites Monitored",
            "Please select",
            showcase=ICONS["site"],
            theme="bg-gradient-orange-red",
        )
        return ui.value_box(
            "Total Swim Sites Monitored",
            f"{total:,} Swim Sites",
            showcase=ICONS["site"],
            theme="bg-gradient-orange-red",
            #style="min-height: 150px;"
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
            #style="min-height: 150px;"
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
            #style="min-height: 150px;"
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

# # -------------------- add a map woth high risk areas ------------------------------------------------
    @render_widget
    def beach_map():
        df_filtered = filtered_df()

        # df_filtered["latitude"] = pd.to_numeric(df_filtered["latitude"], errors="coerce")
        # df_filtered["longitude"] = pd.to_numeric(df_filtered["longitude"], errors="coerce")

        # df_filtered = df_filtered.dropna(subset=["latitude", "longitude"])

        m = Map(center=[-33.86, 151.20], zoom=10)

        if df_filtered.empty or not {'latitude', 'longitude', 'enterococci', 'beach'}.issubset(df_filtered.columns):
            return m

        def get_color(level):
            if level <= 40:
                return "#287C8EFF"
            elif level <= 130:
                return "#440154FF"
            else:
                return "#FDE725FF"
          # Aggregate per beach: average enterococci, and take first lat/lon
        df_grouped = (
            df_filtered
            .dropna(subset=["latitude", "longitude"])
            .groupby("beach")
            .agg({
                "enterococci": "mean",
                "latitude": "first",
                "longitude": "first"
            })
            .reset_index()
        )
        def make_marker(row):
                return CircleMarker(
                    location=(row["latitude"], row["longitude"]),
                    radius=5,
                    color=get_color(row["enterococci"]),
                    fill_color=get_color(row["enterococci"]),
                    fill_opacity=0.6,
                    popup=HTML(f"<b>{row['beach']}</b><br>Avg Enterococci: {row['enterococci']:.1f}")
                )
        
        markers = df_grouped.apply(make_marker, axis=1).tolist()
        group = LayerGroup(layers=markers)
        m.add_layer(group)

        return m


# ----------- Server-side render logic for visual answers in FAQ ----------------------------------------------

    @render_plotly
    def faq_high_risk_chart():
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

    @render.data_frame
    def faq_high_risk_df():
        return high_enterococci_sites().head(10)  # Display the top 10 swim sites with high enterococci levels


    @render_plotly
    def faq_seasonal_variation_chart():
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
        
    @render.data_frame
    def faq_seasonal_variation_df():
        return water_quality_by_season().head(10)  # Display the top 10 seasonal variations
   
   
        
      
    chat = qc.server("chat", chat_config)

    @render.data_frame
    def chat_filtered_df():
        return chat.df()
# ------------------------ render the download button -------------------------------------------------------------

    @render.download(filename="filtered_data.csv")
    def download_data():
        df_out = filtered_df()
        return df_out.to_csv(index=False)

#--------------------- reset the filters appliedd -----------------------------------------------------------------
    @reactive.effect
    @reactive.event(input.reset)
    def _():
        ui.update_date_range("daterange", start=DEFAULT_DATE_RANGE[0], end=DEFAULT_DATE_RANGE[1])
        ui.update_checkbox_group("regions",  selected=DEFAULT_REGIONS)
        ui.update_selectize("councils", selected=DEFAULT_COUNCILS)

    
app = App(app_ui, server)