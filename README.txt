FlightScope - Running Instructions

Follow these step-by-step instructions to set up and run the FlightScope application on your local machine.

=========================================
STEP 1: Prerequisites & Initial Setup
=========================================
1. Ensure you have Python (version 3.8 or higher) installed on your system.
2. Open a terminal or command prompt.
3. Navigate into the cloned project root directory (e.g., FlightScope or whatever you named the clone):
   cd FlightScope

4. (Optional but Highly Recommended) Create a virtual environment to avoid dependency conflicts:
   python -m venv .venv

5. Activate the virtual environment:
   - On Windows:
     .venv\Scripts\activate
   - On macOS/Linux:
     source .venv/bin/activate

6. Install the required Python libraries:
   pip install -r requirements.txt


=========================================
STEP 2: Data Setup 
=========================================
Because the dataset is very large, it is not included in this repository. 
You will need to download the pre-processed data files to run the dashboard.

1. Create a folder named "processed" inside the "data" directory. The path should be:
   data/processed/

2. Download the pre-processed files from our Google Drive:
   - Link: https://drive.google.com/drive/folders/1Gxms7jueCaMbZjSNk3rzNzUc66H2XH2j?usp=sharing

3. You need to download the following 2 files:
   - `flights.db` (The core database)
   - `processed_flights_with_umap.parquet` (For High-Dimensional Analytics)

4. Place all 2 files directly into the `data/processed/` directory.


=========================================
STEP 3: Running the Dash Application
=========================================
Once the data is in place, you are ready to launch the visual analytics dashboard.

1. From the project root directory, start the application by running:
   python src/app/app.py
2. You will see output in the terminal indicating that the Flask/Dash server has started.
3. Open your web browser (Chrome, Firefox, Edge, etc.).
4. Navigate to the local web address provided in the terminal. It is typically:
   http://127.0.0.1:8050/

You should now see the FlightScope interactive dashboard!
