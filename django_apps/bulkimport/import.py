import sys
sys.path.append('/home/merriman')
sys.path.append('/home/merriman/merrimanriver.com')

from django.http import HttpResponse, Http404
from django.core import serializers
import time
import csv
import sys
import MySQLdb
import codecs

try:
    import json
except ImportError:
    from django.utils import simplejson as json
import logging
logging.basicConfig(
    level       = logging.DEBUG,
    format      = '%(asctime)s %(levelname)s %(message)s',
    filename    = '/home/merriman/merrimanriver.com/logs/threaded_call.log',
    filemode    = 'a'
)

def cursor_fetch(cursor):
    columns = cursor.description
    result = [{columns[index][0]: column for index, column in enumerate(value)} for value in cursor.fetchall()]
    return result[0]

def cursor_fetchall(cursor):
    columns = cursor.description
    return [{columns[index][0]: column for index, column in enumerate(value)} for value in cursor.fetchall()]

class ContinueOuterLoop( Exception ):
    pass

def main(job_id):
    db = MySQLdb.connect(
        host="localhost",
        user="merriman",
        passwd="W8gT5KD",
        db="vote_merrimanriver_com"
    )
    cur = db.cursor()
    """
        Main workhorse of bulkimport--this function runs in the background
        (via threading) and works through to complete a job. A fair amount
        of trickery is involved in dynamically inserting to models. The
        basic flow is:

        Iterate through CSV file and, using the job's mapping data, decide
        if we have to look up related objects. Combine all arguments and
        finally create() the object. A record is kept for all created
        objects so that we can delete imported records.
    """

    # We MUST wait until the calling script finishes BEFORE ANY of the DB queries will
    # hit the database. So, we put this process to sleep a bit.
    time.sleep(1)

    cur.execute("""SELECT * FROM bulkimport_job WHERE id = %s""", (job_id,))
    counter = 0

    while cur.rowcount == 0 and counter < 10:
        counter += 1
        time.sleep(1)
        cur.execute("""SELECT * FROM bulkimport_job WHERE id = %s""", (job_id,))

    original = cursor_fetch(cur)

    if not original['mapping'] or not original['mapping_through']:
        logging.debug("The bulkimport_job record is missing the mapping or mapping_through records.")
        raise Http404

    # Fetch the template so we can find the django_content_type.model we need to work with
    cur.execute("""SELECT c.model FROM django_content_type c WHERE id = (SELECT content_type_id FROM bulkimport_template WHERE id = %s)""", (original['template_id'],))
    content_type = cursor_fetch(cur)

    insert_table = 'election_'+content_type['model']

    mapping = json.loads(original['mapping'])
    mapping_through = json.loads(original['mapping_through'])
    required = json.loads(original['required'])
    unique = json.loads(original['unique'])

    # original['mapping_through'] = {"ballot": "id", "election": "id"}
    related_models = {}
    for key, value in mapping_through.items():
        related_models[key] = 'election_' + key

    # , encoding='utf-16'
    with open('/home/merriman/merrimanriver.com/source/media/' + original['data'], 'r') as file:
        read_file = file.readlines()
    csv_count = len(read_file)

    lines = csv.reader(read_file)

    added = 0

    if not mapping:
        cur.execute("""UPDATE bulkimport_job SET status = 'failed' WHERE id = %s""", (job_id,))
        db.commit()
        return HttpResponse(True)


    for line in lines:
        try:
            args = {}
            do_not_add = False
            for k, v in mapping.items():
                if v is not None:
                    try:
                        val = line[int(v)].strip()
                    except Exception:
                        continue

                    # If the field is required, check to make sure there is a value
                    if required and k in required:
                        if not val or val == '':
                            logging.debug("Missing %ss required value", k)
                            do_not_add = True
                            print("Set Do_Not_Add to True on line 124")
                            try:
                                sql_string = """INSERT INTO bulkimport_error (job_id, data, message) VALUES (%s, %s, %s)"""
                                cur.execute(sql_string, (job_id, json.dumps(line), "Missing required field"))
                                db.commit()
                            except Exception:
                                logging.debug("Error inserting bulkimport_error: %s, %s, %s" % (job_id, json.dumps(line), "Missing required field"))

                            break

                    # If the field is unique, check to make sure it doesn't already exist
                    if unique and k in unique:
                        try:
                            sql_string = """SELECT id FROM """+insert_table+""" WHERE %s = '%s'""" % (k, val)
                            cur.execute(sql_string)
                            c = cur.rowcount

                        except Exception as e:
                            # This could have failed because the unique field is a foreign key, meaning it needs a '_id' appended to the name.
                            # So, we try again with a new field name.
                            try:
                                field = str(k) + '_id'
                                sql_string = """SELECT id FROM """ + insert_table + """ WHERE %s = '%s'""" % (field, val)
                                cur.execute(sql_string)
                                c = cur.rowcount

                            except Exception as e:
                                do_not_add = True
                                print("Set Do_Not_Add to True on line 152")
                                logging.debug("Error fetching unique count: %s" % (e,))
                                break

                        if c > 0:
                            do_not_add = True
                            print("Set Do_Not_Add to True on line 149")
                            try:
                                cur.execute("""INSERT INTO bulkimport_error (job_id, data, message) VALUES (%s, %s, %s)""", (job_id, json.dumps(line), "Duplicate value for unique field"))
                                db.commit()
                            except Exception:
                                logging.debug("Error inserting bulkimport_error: %s, %s, %s" % (job_id, json.dumps(line), "Duplicate value for unique field"))

                            break

                    try:
                        # If there's a related field
                        relation = mapping_through[k] # k='ballot', relation='id' : 'pin', relation='id' (disable)

                    except (KeyError, TypeError):
                        # No relation, so straight key=value
                        args[str(k)] = val

                    else:
                        # This looks for a header file (the id cannot be a string (header).
                        # if it finds one, it ignores this line and continues on.
                        if (relation == 'id') and not val.isdigit():
                            raise ContinueOuterLoop

                        if k in related_models:
                            # FK field
                            # Get the record from the DB that this input has a foreign key to.
                            if relation == 'id':
                                sql_string = """SELECT COUNT(*) as count FROM """ + related_models[k] + """ WHERE %s = %s""" % (relation, val)
                            else:
                                sql_string = """SELECT COUNT(*) as count FROM """ + related_models[k] + """ WHERE %s = '%s'""" % (relation, val)

                            cur.execute(sql_string)
                            result = cursor_fetch(cur)

                            if result['count'] > 0:
                                # build the foreign key column name by adding the '_id' to the column
                                if relation == 'id' or relation == 'pin':
                                    args[str(k)+'_id'] = val
                                else:
                                    args[str(k)] = val

                            else:
                                if required and k in required:
                                    do_not_add = True
                                    print("Set Do_Not_Add to True on line 204")
                                    try:
                                        msg = "A required %s object was not found by %s='%s'" % (k, relation, val)
                                        cur.execute(
                                            """INSERT INTO bulkimport_error (job_id, data, message) VALUES (%s, %s, %s)""", (job_id, json.dumps(line), msg))
                                        db.commit()
                                    except Exception:
                                        logging.debug("Error inserting bulkimport_error: %s, %s, %s" % (job_id, json.dumps(line), msg))

                                    break


            if not do_not_add and args:
                try:
                    col_string = ''
                    val_string = ''
                    value_list = []
                    loop_count = 0
                    try:
                        for col_key, col_value in args.items():
                            if loop_count == 0:
                                col_string = col_key
                                val_string = '%s'
                                value_list.append(col_value)
                                loop_count += 1
                            else:
                                col_string = col_string + ', ' + col_key
                                val_string = val_string + ', ' + '%s'
                                value_list.append(col_value)

                        value_list = tuple(value_list)
                    except Exception as e:
                        logging.debug("Unable to loop through the vars: %s", (e,))

                    try:
                        sql_string = """INSERT INTO """+insert_table+""" ("""+col_string+""") VALUES ("""+val_string+""")"""
                        cur.execute(sql_string, value_list)
                        db.commit()
                        inserted = cur.lastrowid

                    except Exception as e:
                        logging.debug("There was an error generating or executing the INSERT string: %s", (e,))
                        logging.debug("Column names: " + col_string)
                        logging.debug("Column placeholders: " + val_string)
                        logging.debug("Column values: " + ':'.join(map(str, value_list)))
                        break

                    cur.execute("""INSERT INTO bulkimport_log (content_type_id, job_id, remote_pk) VALUES (%s, %s, %s)""", (original['content_type_id'], job_id, inserted))
                    db.commit()

                    added += 1

                except Exception:
                    arg_json = {}
                    try:
                        arg_json = json.dumps(args)

                    except TypeError:
                        for k, v in args.items():
                            try:
                                arg_json[k] = serializers.serialize("json", [v])
                            except:
                                pass

                        arg_json = json.dumps(arg_json)

                    # if required and required.has_key(k):
                    #     message = "Couldn't add row (%s)" % e
                    #     cur.execute("""INSERT INTO bulkimport_error (job_id, data, message, extra) VALUES (%s, %s, %s, %s)""", (job_id, json.dumps(line), message, arg_json))
                    #     db.commit()

            else:
                if do_not_add:
                    print("Do Not Add is True")
                else:
                    print("Do Not Add is False")

        except ContinueOuterLoop:
            pass

    # Update the status in the Job Model, bulkimport_job table.
    if csv_count < 3 and added == 0 or added > 0:
        new_status = 'complete'
    else:
        new_status = 'failed'

    cur.execute("""UPDATE bulkimport_job SET status = %s WHERE id = %s""", (new_status, job_id))
    db.commit()

    cur.close()
    db.close()


if __name__ == "__main__":
    main(sys.argv[1])