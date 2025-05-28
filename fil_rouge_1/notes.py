"""amine-8kkh@amine-8kkh-ThinkBook-14-G2-ITL:~/Desktop/amine/VS_project/fil_rouge_1$ docker exec -it kafka bash 
[appuser@kafka ~]$ kafka-topics --list --bootstrap-server localhost:9092

[appuser@kafka ~]$ kafka-topics.sh --create --topic traffic-data --bootstrap-server kafka:9092 --partitions 1 --replication-factor 1
bash: kafka-topics.sh: command not found
[appuser@kafka ~]$ kafka-topics --create --topic traffic-data --bootstrap-server kafka:9092 --partitions 1 --replication-factor 1
Created topic traffic-data.
[appuser@kafka ~]$ kafka-topics --list --bootstrap-server localhost:9092
traffic-data
[appuser@kafka ~]$ kafka-console-producer --topic traffic-data --bootstrap-server kafka:9092
>{"timestamp": "2025-03-20T10:00:00", "vehicles": 5}
>{"timestamp": "2025-03-20T10:00:01", "vehicles": 7}
>^C[appuser@kafka ~]$ kafka-console-consumer --topic traffic-data --bootstrap-server kafka:9092 --from-beginning
{"timestamp": "2025-03-20T10:00:00", "vehicles": 5}"""

