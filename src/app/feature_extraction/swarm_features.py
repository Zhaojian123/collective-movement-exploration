from model.dataset_model import Dataset
from db import create_session


def calculate_swarm_features(id):
    """ Calculate swarm features

    Keyword arguments:
    id -- dataset id

    """
    # create a new threaded database session
    session = create_session()
    # Query the dataset with the id
    dataset = session.query(Dataset).filter_by(id=id)
    dataset[0].status = 'Calculating swarm features'
    dataset[0].progress = 50
    session.commit()

    # for every animal get the movement data
    # and extrat the absolute features
    try:
        # calculate the centroid
        calculate_centroid(id, session)
        # calculate the absolute feature distance to centroid
        calculate_distance_centroid(id, session)
        # calculate the medoid of the group
        calculate_medoid(id, session)
        # calculate the convex hull area
        calculate_convex_hull(id, session)
        # calculate convex hull area
        calculate_convex_hull_area(id, session)
        # calculate delaunay triangulation
        calculate_delaunay_triangulation(id, session)
        # calculate voronoi diagram
        calculate_voronoi_diagram(id, session)
        # calculate metric distance, speed and acceleration
        calculate_speed_acceleration(id, session)
        # ToDO change this here sometime
        dataset[0].status = 'Complete'
        dataset[0].progress = 100
    except Exception as e:
        # Something went wrong when calculating swarm features
        session.rollback()
        dataset[0].status = 'Error - calculating swarm features: ' + str(e)[0:200]
        dataset[0].error = True
        pass
    # commit the changes
    session.commit()

    # remove the session
    session.remove()


def calculate_centroid(id, session):
    """ Calculate the centroid of the animal group

    Keyword arguments:
    id - id of the dataset
    session - db session
    """
    query = '''UPDATE   group_data
                SET 	centroid =  subquery.geom
                FROM ( SELECT "time", ST_Centroid(ST_Collect(position)) AS geom
                                        FROM movement_data
                                        WHERE dataset_id = :id
                                        GROUP BY "time") AS subquery
                WHERE   group_data.time = subquery.time
                        AND group_data.dataset_id = :id;'''
    session.execute(query, {'id': id})


def calculate_distance_centroid(id, session):
    """ Calculate the absolute feature distance centroid

    Keyword arguments:
    id - id of the dataset
    session - db session
    """
    query = '''UPDATE movement_data
                SET   distance_centroid = subquery.dist
                FROM   (SELECT  tmp."time", tmp.animal_id,ST_Distance(group_data.centroid, tmp.position) AS dist
                        FROM group_data, movement_data as tmp
                        WHERE   group_data.time = tmp.time
                                AND group_data.dataset_id = :id
                                AND tmp.dataset_id = :id)  AS subquery
                WHERE   movement_data.time = subquery.time
                        AND movement_data.dataset_id = :id
                        AND movement_data.animal_id = subquery.animal_id;'''
    session.execute(query, {'id': id})


def calculate_medoid(id, session):
    """ Calculate the medoid of the whole group

    Keyword arguments:
    id - id of the dataset
    session - db session
    """
    query = '''UPDATE group_data
                SET medoid = movement_data.animal_id
                FROM (SELECT "time", min(distance_centroid) as min_centroid
                                                    FROM movement_data
                                                    WHERE dataset_id = :id
                                                    GROUP BY "time") AS subquery, movement_data
                WHERE   group_data.dataset_id = :id
                        AND group_data.time = movement_data.time
                        AND movement_data.dataset_id = :id
                        AND movement_data.time = subquery.time
                        AND movement_data.distance_centroid = subquery.min_centroid;'''
    session.execute(query, {'id': id})


def calculate_convex_hull(id, session):
    """ Calculate the convex hull of the animal group

    Keyword arguments:
    id - id of the dataset
    session - db session
    """
    query = '''UPDATE group_data
                SET 	convex_hull = subquery.geom
                FROM (  SELECT "time", ST_ConvexHull(ST_Collect(position)) AS geom
                        FROM movement_data
                        WHERE dataset_id = :id
                        GROUP BY "time") AS subquery
                WHERE  group_data.time = subquery.time
                    AND group_data.dataset_id = :id; '''
    session.execute(query, {'id': id})


def calculate_convex_hull_area(id, session):
    """ Calculate the convex hull area of the animal group

    Keyword arguments:
    id - id of the dataset
    session - db session
    """
    query = '''UPDATE group_data
                SET 	convex_hull_area = subquery.area
                FROM (  SELECT "time", ST_Area(convex_hull) AS area
                        FROM group_data
                        WHERE dataset_id = :id) AS subquery
                WHERE  group_data.time = subquery.time
                    AND group_data.dataset_id = :id; '''
    session.execute(query, {'id': id})


def calculate_delaunay_triangulation(id, session):
    """ Calculate the delaunay triangulation of the animal group

    Keyword arguments:
    id - id of the dataset
    session - db session
    """
    query = '''UPDATE group_data
                SET 	delaunay_triangulation = subquery.geom
                FROM (  SELECT "time", ST_DelaunayTriangles(ST_Collect(position),0,1) AS geom
                        FROM movement_data
                        WHERE dataset_id = :id
                        GROUP BY "time") AS subquery
                WHERE  group_data.time = subquery.time
                    AND group_data.dataset_id = :id; '''
    session.execute(query, {'id': id})


def calculate_voronoi_diagram(id, session):
    """ Calculate the voronoi diagram of the animal group

    Keyword arguments:
    id - id of the dataset
    session - db session
    """
    query = '''
                UPDATE
                    group_data
                SET 	voronoi_polygons = subquery.geom
                FROM (  SELECT "time", ST_VoronoiPolygons(ST_Collect(position)) AS geom
                        FROM movement_data
                        WHERE dataset_id = :id
                        GROUP BY "time") AS subquery
                WHERE  group_data.time = subquery.time
                    AND group_data.dataset_id = :id; '''
    session.execute(query, {'id': id})


def calculate_speed_acceleration(id, session):
    """ Calculate the SUM metric distance, AVG speed and AVG acceleration of the animal group

    Keyword arguments:
    id - id of the dataset
    session - db session
    """
    # metric distance
    query = '''UPDATE group_data
                SET metric_distance = subquery.distance
                FROM (  SELECT "time", SUM(metric_distance) as distance
                        FROM movement_data
                        WHERE dataset_id = :id
                        GROUP BY "time") as subquery
                WHERE group_data.time = subquery.time
                      AND group_data.dataset_id = :id;'''
    session.execute(query, {'id': id})

    # speed
    query = '''UPDATE group_data
                SET speed = subquery.speed
                FROM (  SELECT "time", SUM(speed) as speed
                        FROM movement_data
                        WHERE dataset_id = :id
                        GROUP BY "time") as subquery
                WHERE group_data.time = subquery.time
                      AND group_data.dataset_id = :id;'''
    session.execute(query, {'id': id})

    # acceleration
    query = '''UPDATE group_data
                SET acceleration = subquery.acceleration
                FROM (  SELECT "time", SUM(acceleration) as acceleration
                        FROM movement_data
                        WHERE dataset_id = :id
                        GROUP BY "time") as subquery
                WHERE group_data.time = subquery.time
                      AND group_data.dataset_id = :id;'''
    session.execute(query, {'id': id})