import mysql.connector
from mysql.connector import errorcode
from datetime import date, datetime, timedelta

try:
    cnx = mysql.connector.connect(user='monkeydb', password='monkeydb',
                                  host='pneuromdbcit.services.brown.edu',
                                  database='mkydb')
except mysql.connector.Error as err:
  if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
    print("Something is wrong with your user name or password")
  elif err.errno == errorcode.ER_BAD_DB_ERROR:
    print("Database does not exist")
  else:
    print(err)
else:
  cnx.close()

query = ("SELECT * FROM Animals ")
cursor = cnx.cursor()
cursor.execute(query)


for (idAnimals, animalName, animalDOB, animalSex, animalPIN, animalSpecies) in cursor:
  print("{}, {}, {}, {}, {}, {}".format(
    idAnimals, animalName, animalDOB, animalSex, animalPIN, animalSpecies))

add_monkey = ("INSERT INTO Animals "
               "(idAnimals, animalName, animalDOB, animalSex, animalPIN, animalSpecies) "
               "VALUES (%(animalID)s, %(animalName)s, %(animalDOB)s, %(animalSex)s, %(animalPIN)s, %(animalSpecies)s)")


monkey = {
    'animalID' : cursor.lastrowid,
    'animalName' : 'Murdoc',
    'animalDOB' : datetime.now().date(),
    'animalSex' : 'Male',
    'animalPIN' : None,
    'animalSpecies' : 'Male',
    }
add_monkey % monkey
cursor.execute(add_monkey % monkey)
cnx.commit()

cursor.close()
cnx.close()
