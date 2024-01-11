run:
	poetry run streamlit run midiroll/roll.py

main:
	poetry run python -m midiroll
      
jupyter:
	poetry run jupyter lab
    
requirements.txt:
	pipreqs . --force
