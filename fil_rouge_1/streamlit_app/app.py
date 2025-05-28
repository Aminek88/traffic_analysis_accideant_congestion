import streamlit as st
import redis
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import time
from streamlit_autorefresh import st_autorefresh

# Redis connection
try:
    r = redis.Redis(host='redis', port=6379, decode_responses=True)
except redis.RedisError as e:
    st.error(f"Erreur de connexion à Redis: {e}")
    r = None

# Streamlit app
st.title("Tableau de bord du trafic en temps réel")

# Rafraîchir toutes les 10 secondes
st_autorefresh(interval=10000)

# Fetch recent detections
def get_detections():
    if not r:
        return pd.DataFrame()
    try:
        data = []
        cursor = '0'
        while cursor != 0:
            cursor, keys = r.scan(cursor=cursor, match="detection:*", count=100)
            for key in keys:
                try:
                    value = r.get(key)
                    if value:
                        detection = json.loads(value)
                        data.append(detection)
                except json.JSONDecodeError as e:
                    st.error(f"Erreur de parsing JSON pour la clé {key}: {e}")
        df = pd.DataFrame(data)
        if not df.empty:
            # Calculer x_delta, y_delta, x_velocity, y_velocity
            df = df.sort_values(['track_id', 'frame_id'])
            df['x_delta'] = df.groupby('track_id')['x_centre'].diff().fillna(0.0)
            df['y_delta'] = df.groupby('track_id')['y_centre'].diff().fillna(0.0)
            df['x_velocity'] = df['x_delta'] / 30.0
            df['y_velocity'] = df['y_delta'] / 30.0
        return df
    except redis.RedisError as e:
        st.error(f"Erreur de connexion à Redis: {e}")
        return pd.DataFrame()

# Conteneur pour les mises à jour
with st.container():
    df = get_detections()
    if not df.empty:
        # Limiter aux 1000 dernières détections pour la performance
        df = df.tail(1000)

        # Section des métriques et scatter plot en deux colonnes
        col1, col2 = st.columns(2)
        with col1:
            vehicle_count = len(df['track_id'].unique())
            st.metric("Nombre de véhicules", vehicle_count)
        with col2:
            avg_speed = df['x_velocity'].mean() if 'x_velocity' in df.columns else 0
            st.metric("Vitesse moyenne", f"{avg_speed:.2f} px/s")

        scatter_fig = px.scatter(
            df,
            x='x_centre',
            y='y_centre',
            color='track_id',
            size='confiance',
            title="Positions des véhicules",
            labels={'x_centre': 'Position X', 'y_centre': 'Position Y'}
        )
        st.plotly_chart(scatter_fig, use_container_width=True)

        # Tableau des données (en pleine largeur)
        st.subheader("Données des détections")
        display_df = df[['track_id', 'x_centre', 'y_centre', 'frame_id', 'x_velocity', 'y_velocity']]
        if 'confiance' in df.columns:
            display_df = display_df.assign(confiance=df['confiance'])
        # Formater les colonnes numériques pour 2 décimales
        display_df = display_df.round({'x_centre': 2, 'y_centre': 2, 'x_velocity': 2, 'y_velocity': 2, 'confiance': 2})
        st.dataframe(display_df, use_container_width=True)

        # Bar chart pour la densité par classe (en pleine largeur)
        if 'class_name' in df.columns:
            st.subheader("Densité par classe de véhicules")
            class_counts = df['class_name'].value_counts().reset_index()
            class_counts.columns = ['class_name', 'count']
            bar_fig = px.bar(
                class_counts,
                x='class_name',
                y='count',
                title="Nombre de détections par classe",
                labels={'class_id': 'Classe', 'count': 'Nombre de détections'},
                color='class_name',
                color_discrete_sequence=px.colors.qualitative.Plotly
            )
            bar_fig.update_layout(
                xaxis_title="Classe",
                yaxis_title="Nombre de détections",
                showlegend=False,
                height=400
            )
            st.plotly_chart(bar_fig, use_container_width=True)
        else:
            st.warning("Aucune colonne 'class_id' trouvée dans les données. Veuillez vérifier les données Redis.")

        # Visualisation des trajectoires (en pleine largeur, hors colonnes)
        x_min_global = df['x_centre'].min() - 50
        x_max_global = df['x_centre'].max() + 50
        y_min_global = df['y_centre'].min() - 50
        y_max_global = df['y_centre'].max() + 50

        traj_fig = go.Figure()

        unique_track_ids = df['track_id'].unique()
        colors = px.colors.qualitative.Plotly  # Palette corrigée
        track_id_to_color = {track_id: colors[i % len(colors)] for i, track_id in enumerate(unique_track_ids)}

        for track_id in unique_track_ids:
            track_data = df[df['track_id'] == track_id].sort_values('frame_id')
            
            traj_fig.add_trace(
                go.Scatter(
                    x=track_data['x_centre'],
                    y=track_data['y_centre'],
                    mode='lines',
                    name=f'ID {int(track_id)}',
                    line=dict(color=track_id_to_color[track_id], width=2),
                    opacity=0.7,
                    legendgroup=f'ID {int(track_id)}',
                    showlegend=True
                )
            )
            
            traj_fig.add_trace(
                go.Scatter(
                    x=track_data['x_centre'],
                    y=track_data['y_centre'],
                    mode='markers',
                    name=f'ID {int(track_id)}',
                    marker=dict(
                        color=track_id_to_color[track_id],
                        size=6,
                        opacity=0.5
                    ),
                    legendgroup=f'ID {int(track_id)}',
                    showlegend=False
                )
            )

        traj_fig.update_layout(
            title="Trajectoires des Véhicules (Centres des Boîtes Englobantes)",
            xaxis_title="X Centre (pixels)",
            yaxis_title="Y Centre (pixels)",
            xaxis=dict(range=[x_min_global, x_max_global]),
            yaxis=dict(range=[y_min_global, y_max_global]),
            showlegend=True,
            height=600
        )

        st.plotly_chart(traj_fig, use_container_width=True)

    else:
        st.warning("Aucune donnée disponible pour le moment.")