# Roda a extração dividida em 4 processos paralelos
rodar4:
	python3 main.py --parte 1 --total 4 & \
	python3 main.py --parte 2 --total 4 & \
	python3 main.py --parte 3 --total 4 & \
	python3 main.py --parte 4 --total 4 & \
	wait
	echo "Todos os 4 processos terminaram!"

# Roda a extração dividida em 6 processos paralelos
rodar6:
	python3 main.py --parte 1 --total 6 & \
	python3 main.py --parte 2 --total 6 & \
	python3 main.py --parte 3 --total 6 & \
	python3 main.py --parte 4 --total 6 & \
	python3 main.py --parte 5 --total 6 & \
	python3 main.py --parte 6 --total 6 & \
	wait
	echo "Todos os 6 processos terminaram!"
