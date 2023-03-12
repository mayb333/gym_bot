import psycopg2
import csv
from config import host, db_name


class DataBase:

    def __init__(self):
        self.host = host
        self.db_name = db_name

    def connect_to_db(self):
        connection = psycopg2.connect(
            host=self.host,
            database=self.db_name
        )
        print('[INFO] connected to db')

        return connection

    # Check if (date, username) is not in 'weights' already
    def user_not_in_weights_for_certain_date(self, date, user_id):
        try:
            connection = self.connect_to_db()

            with connection.cursor() as cursor:
                query = f"""SELECT date, user_id
                            FROM weights
                            WHERE date = '{date}' AND user_id = '{user_id}';"""
                cursor.execute(query)
                result = cursor.fetchone()
                if result is None:
                    connection.close()
                    print('[INFO] connection closed')
                    return True
                connection.close()
                print('[INFO] connection closed')
                return False

        except Exception as exp:
            print('[!] Couldn\'t commit the function "user_not_in_weights_for_certain_date"\n', exp)

    # Write user's weight for today
    def write_to_weights(self, date, user_id, weight):
        try:
            connection = self.connect_to_db()

            with connection.cursor() as cursor:
                query = f"""INSERT INTO weights (date, user_id, weight) 
                                          VALUES('{date}', '{user_id}', '{weight}')"""

                cursor.execute(query)
                connection.commit()
                print('[INFO] User\'s weight data has been added!')

                connection.close()
                print('[INFO] connection closed')
        except Exception as exp:
            print('[!] Couldn\'t commit the function "write_to_weights"\n', exp)

    def write_to_proteins(self, date, datetime, user_id, meal_id, meal_name, grams, proteins):
        try:
            connection = self.connect_to_db()

            with connection.cursor() as cursor:
                query = f"""INSERT INTO proteins (date, datetime, user_id, meal_id, meal_name, grams, proteins) 
                                          VALUES('{date}', '{datetime}', '{user_id}', '{meal_id}', '{meal_name}', 
                                          '{grams}', '{proteins}')"""

                cursor.execute(query)

                connection.commit()
                print('[INFO] User\'s proteins data has been added!')

                connection.close()
                print('[INFO] connection closed')
        except Exception as exp:
            print(f'[!] Couldn\'t commit the function "write_to_proteins"\n', exp)

    def set_meal_id(self, date, user_id):
        try:
            connection = self.connect_to_db()

            with connection.cursor() as cursor:
                query = f"""SELECT meal_id
                            FROM proteins 
                            WHERE date = '{date}' AND user_id = '{user_id}'"""

                cursor.execute(query)

                result = cursor.fetchall()
                if result:
                    meal_id = int(result[-1][0])
                else:
                    meal_id = 0
                connection.close()
                print('[INFO] connection closed')
                return meal_id
        except Exception as exp:
            print(f'[!] Couldn\'t commit the function "set_meal_id"\n', exp)

    def import_from_weights_sql_to_csv(self, user_id, date):
        try:
            connection = self.connect_to_db()
            csv_path = f'users_csv_data/weights_data_{user_id}_{date}.csv'

            with connection.cursor() as cursor:
                query = f"""SELECT date, weight
                            FROM weights 
                            WHERE user_id = '{user_id}'"""

                cursor.execute(query)
                rows = cursor.fetchall()

                connection.close()
                print('[INFO] connection closed')

            if rows:
                result = []
                column_names = []

                for item in cursor.description:
                    column_name = item[0]
                    column_names.append(column_name)

                result.append(column_names)
                for row in rows:
                    result.append(list(row))

                with open(csv_path, 'w') as file:
                    writer = csv.writer(file, delimiter=';')
                    for row in result:
                        writer.writerow(row)

                return 'File is created'
            else:
                return 'No data found'

        except Exception as exp:
            print(f'[!] Couldn\'t commit the function "import_from_weights_sql_to_csv"\n', exp.with_traceback())
            return 'Problem occurred'

    def import_from_proteins_sql_to_csv(self, user_id, date):
        try:
            connection = self.connect_to_db()
            csv_path = f'users_csv_data/proteins_data_{user_id}_{date}.csv'

            with connection.cursor() as cursor:
                query = f"""SELECT date, meal_id, meal_name, grams, proteins
                            FROM proteins
                            WHERE user_id = '{user_id}'"""

                cursor.execute(query)
                rows = cursor.fetchall()

                connection.close()
                print('[INFO] connection closed')

            if rows:
                result = []
                column_names = []

                for item in cursor.description:
                    column_name = item[0]
                    column_names.append(column_name)

                result.append(column_names)
                for row in rows:
                    result.append(list(row))

                with open(csv_path, 'w') as file:
                    writer = csv.writer(file, delimiter=';')
                    for row in result:
                        writer.writerow(row)

                return 'File is created'
            else:
                return 'No data found'

        except Exception as exp:
            print(f'[!] Couldn\'t commit the function "import_from_proteins_sql_to_csv"\n', exp.with_traceback())
            return 'Problem occurred'

    def create_weights_table(self):
        try:
            connection = self.connect_to_db()

            # create 'weights' table
            with connection.cursor() as cursor:
                cursor.execute(
                    """CREATE TABLE weights(
                        date varchar(20) NOT NULL,
                        user_id varchar(20) NOT NULL,
                        weight varchar(20) NOT NULL);""")
                connection.commit()
                print('[INFO] Table "weights" created')
        except Exception as exp:
            print('[!] Couldn\'t commit the function "create_weights_table"\n', exp)

    def create_proteins_table(self):
        try:
            connection = self.connect_to_db()

            with connection.cursor() as cursor:
                cursor.execute(
                    """CREATE TABLE proteins(
                        date varchar(50) NOT NULL,
                        datetime varchar(50) NOT NULL,
                        user_id varchar(50) NOT NULL,
                        meal_id varchar(10) NOT NULL,
                        meal_name varchar(50) NOT NULL,
                        grams varchar(50) NOT NULL,
                        proteins varchar(50) NOT NULL);""")
                connection.commit()
                print('[INFO] Table "proteins" created')

                connection.close()
                print('[INFO] connection closed')

        except Exception as exp:
            print('[!] Couldn\'t commit the function "create_proteins_table"\n', exp)


def main():
    database = DataBase()
    # database.import_from_weights_sql_to_csv('961372820222', '2023-03-11')
    # kek = database.import_from_proteins_sql_to_csv('872800942', '2023-03-11')
    # database.create_proteins_table()
    # database.write_to_proteins('2023-01-02', 'lol', '08', '2', 'cheburek', '200', '20')
    # print(database.set_meal_id('2023-01-02', '08'))
    # database.set_meal_id('2023-01-02', '084')


if __name__ == '__main__':
    main()
