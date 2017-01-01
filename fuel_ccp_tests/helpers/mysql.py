def populate_data(remote, pod, namespace, db_name, table_name, value):
    query = ("CREATE DATABASE {0}; USE {0}; CREATE TABLE {1}"
             " (id int NOT NULL PRIMARY KEY AUTO_INCREMENT, val int);"
             " INSERT INTO {1} (val) VALUES"
             " ({2})").format(db_name, table_name, value)
    remote.check_call("kubectl exec -i {} --namespace={} -c galera"
                      " -- mysql -uroot -ppassword"
                      " -e \"{}\"".format(pod, namespace, query))


def check_data(remote, pod, namespace, db_name, table_name, value):
    query = "SELECT * FROM {db}.{table} WHERE" \
            " val = \"{value}\"".format(db=db_name, table=table_name,
                                        value=value)
    remote.check_call("kubectl exec -i {} --namespace={} -c galera"
                      " -- mysql -uroot -ppassword"
                      " -e \"{}\"".format(pod, namespace, query))
