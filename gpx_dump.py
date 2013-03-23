import psycopg2
from xml.dom.minidom import Document
import argparse
import os
import errno
import sys
import datetime


def status_line(text):
    sys.stdout.write(text)
    sys.stdout.write('\r')
    sys.stdout.flush()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Dumps GPX files from the OSM railsport database schema.")

    # Postgres options
    parser.add_argument("--host",
        help="postgres server host",
        required=True)
    parser.add_argument("--user",
        help="postgres user name",
        required=True)
    parser.add_argument("--password",
        help="postgres user password",
        required=True)
    parser.add_argument("--database",
        help="postgres database name",
        required=True)

    # GPX dumping options
    parser.add_argument("--privacy",
        help="select which privacy levels to write out",
        choices=['public', 'identifiable', 'trackable', 'private'],
        default=['public', 'identifiable', 'trackable'])
    parser.add_argument("--output",
        help="output directory to fill with resulting GPX files",
        default=".")
    parser.add_argument("--metadata",
        help="file inside output directory to write metadata about uploaded GPX files (tags, visibility, etc.)",
        default="metadata.xml")

    args = parser.parse_args()

    if not os.path.exists(args.output):
        sys.stderr.write("Output directory doesn't exist.\n")
        sys.exit(-1)

    if os.path.exists("%s/%s" % (args.output, args.metadata)):
        sys.stderr.write("Metadata file already exists.\n")
        sys.exit(-1)

    doc = Document()
    metadata_file = open("%s/%s" % (args.output, args.metadata), 'w')
    metadata_file.write('<gpxFiles generator="OpenStreetMap gpx_dump.py" timestamp="%s">\n' % datetime.datetime.utcnow().replace(microsecond=0).isoformat())

    conn = psycopg2.connect(database=args.database, user=args.user, password=args.password, host=args.host)
    file_cursor = conn.cursor(name='gpx_files')
    tags_cursor = conn.cursor(name='gpx_file_tags')
    point_cursor = conn.cursor(name='gpx_points')

    print "Mapping user IDs."
    user_map = dict()
    user_cursor = conn.cursor(name='users')
    # user_cursor.execute("SELECT id,display_name FROM users")
    user_cursor = [[None, 53, "foobar"], [None, 54, "barbar"]]
    for user in user_cursor:
        user_map[user[1]] = user[2]
    print "Mapped %s user ids." % (len(user_map))

    files_so_far = 0

    print "Writing traces."
    for d in ('public', 'trackable', 'private', 'identifiable'):
        path = '%s/%s' % (args.output, d)
        try:
            os.makedirs(path)
        except OSError as exc:
            if exc.errno == errno.EEXIST and os.path.isdir(path):
                pass
            else:
                raise

    # file_cursor.execute("""SELECT id,user_id,timestamp,name,description,size,latitude,longitude,visibility
    #                        FROM gpx_files
    #                        WHERE inserted=true AND visible=true AND visibility='public'
    #                        ORDER BY id""")
    file_cursor = [[None, 100, 53, datetime.datetime.utcnow(), "name", "description", 1500, 45.0, -92.42, 'public'],
                   [None, 101, 54, datetime.datetime.utcnow(), "tasdda", "aowogjgja", 1000, 40.2, -91.12, 'trackable'],
                   [None, 102, 54, datetime.datetime.utcnow(), "thoawl", "k1jakmjks", 1000, 43.4, -93.45, 'private'],
                   [None, 103, 53, datetime.datetime.utcnow(), "kjassi", "oiwkcnqjs", 1000, 54.2, -101.2, 'identifiable']]
    for row in file_cursor:
        if row[9] == 'private':
            continue

        # Write out the metadata about this GPX file to the metadata list
        filesElem = doc.createElement("gpxFile")
        filesElem.setAttribute("id", str(row[1]))
        filesElem.setAttribute("timestamp", row[3].isoformat())
        filesElem.setAttribute("description", row[5])
        filesElem.setAttribute("points", str(row[6]))
        filesElem.setAttribute("startLatitude", str(row[7]))
        filesElem.setAttribute("startLongitude", str(row[8]))
        filesElem.setAttribute("visibility", row[9])

        # Only write out user information if it's identifiable or public
        if row[2] and row[9] in ('identifiable', 'public'):
            filesElem.setAttribute("uid", str(row[2]))

            if row[2] in user_map:
                filesElem.setAttribute("user", user_map.get(row[2]))

        # tags_cursor.execute("""SELECT tag FROM gpx_file_tags WHERE gpx_id=%s""", (row[1]))
        tags_cursor = [[None, 'foo'], [None, 'bar']]

        for tag in tags_cursor:
            tagElem = doc.createElement("tag")
            tagElem.appendChild(doc.createTextNode(tag[1]))
            filesElem.appendChild(tagElem)

        # Write out GPX file
        # Important to note that we are not including timestamp here because it's public.
        # See http://wiki.openstreetmap.org/wiki/Visibility_of_GPS_traces
        # point_cursor.execute("""SELECT latitude,longitude,altitude,trackid,timestamp
        #                         FROM gps_points
        #                         WHERE gpx_id=%s
        #                         ORDER BY trackid ASC, tile ASC, latitude ASC, longitude ASC""", (row[1]))
        point_cursor = [[None, 450129224, -924294825, 412.5, 1, datetime.datetime.utcnow()],
                        [None, 451129224, -925294825, 400.2, 1, datetime.datetime.utcnow()],
                        [None, 452129224, -926294825, 310.2, 2, datetime.datetime.utcnow()],
                        [None, 453129224, -927294825, 310.4, 2, datetime.datetime.utcnow()]]

        gpxDoc = Document()
        gpxElem = gpxDoc.createElement("gpx")
        gpxElem.setAttribute("xmlns", "http://www.topografix.com/GPX/1/0")
        gpxElem.setAttribute("version", "1.0")
        gpxElem.setAttribute("creator", "OSM gpx_dump.py")
        gpxDoc.appendChild(gpxElem)

        trackid = None
        for point in point_cursor:
            if trackid is None or trackid != point[4]:
                trackid = point[4]
                trkElem = gpxDoc.createElement("trk")
                nameElem = gpxDoc.createElement("name")
                nameElem.appendChild(gpxDoc.createTextNode("Track %s" % (trackid)))
                trkElem.appendChild(nameElem)

                numberElem = gpxDoc.createElement("number")
                numberElem.appendChild(gpxDoc.createTextNode(str(trackid)))
                trkElem.appendChild(numberElem)

                segmentElem = gpxDoc.createElement("trkseg")
                trkElem.appendChild(segmentElem)
                gpxElem.appendChild(trkElem)

            ptElem = gpxDoc.createElement("trkpt")
            ptElem.setAttribute("lat", "%0.7f" % (float(point[1]) / (10 ** 7)))
            ptElem.setAttribute("lon", "%0.7f" % (float(point[2]) / (10 ** 7)))
            if point[3]:
                eleElem = gpxDoc.createElement("ele")
                eleElem.appendChild(gpxDoc.createTextNode("%0.2f" % point[3]))
                ptElem.appendChild(eleElem)

            if point[5] and row[9] in ('identifiable', 'trackable'):
                timeElem = gpxDoc.createElement("time")
                timeElem.appendChild(gpxDoc.createTextNode(point[5].isoformat()))
                ptElem.appendChild(timeElem)

            segmentElem.appendChild(ptElem)

        file_path = "%s/%s/%07d.gpx" % (args.output, row[9], row[1])
        gpx_file = open(file_path, 'w')
        gpx_file.write(gpxDoc.toprettyxml(' ', encoding='utf-8'))
        gpx_file.close()

        filesElem.setAttribute("filename", file_path)
        metadata_file.write(filesElem.toprettyxml(' ', encoding='utf-8'))

        files_so_far += 1

        if files_so_far % 1000 == 0:
            status_line("Wrote out %7d GPX files." % files_so_far)

    print "Wrote out %7d GPX files." % files_so_far

    metadata_file.write('</gpxFiles>\n')
    metadata_file.close()
