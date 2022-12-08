run:
	poetry run streamlit run midiroll/roll.py
      
jupyter:
	poetry run jupyter lab
    
requirements.txt:
	pipreqs . --force
