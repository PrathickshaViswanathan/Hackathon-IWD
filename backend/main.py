from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles  # To serve static files (plot image)
import pandas as pd
import shutil
import os
import logging
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json  # For structured streaming responses
from ollama_async_ui_test import process_dataframe, plot_image
import time


app = FastAPI()

# Configure CORS (Restrict in Production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (adjust in production)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create uploads directory if not exists
UPLOAD_DIRECTORY = "uploads"
os.makedirs(UPLOAD_DIRECTORY, exist_ok=True)

# Serve static files (plot image)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

@app.post("/uploadfile/")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename.endswith('.xlsx'):
        raise HTTPException(status_code=400, detail="Only .xlsx files are allowed.")

    file_location = os.path.join(UPLOAD_DIRECTORY, file.filename)
    basename, _ = os.path.splitext(file.filename)
    output_filename = os.path.join(UPLOAD_DIRECTORY, basename + '_ui_output.xlsx')

    # Save the uploaded file to disk
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        df = pd.read_excel(file_location) 
        batch_size = 10  # Process 10 rows at a time
        total_batches = (len(df) // batch_size) + (1 if len(df) % batch_size else 0)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

    async def stream_batches():
        """Stream batch results as they're processed."""
        processed_df = pd.DataFrame()
        batch_tracker = set()  # Track processed batch numbers
        
        for batch_num in range(total_batches):
            if batch_num in batch_tracker:  # Skip if batch already processed
                continue
                
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(df))
            df_chunk = df.iloc[start_idx:end_idx]
            
            logging.info("Processing batch %d/%d", batch_num + 1, total_batches)
            batch_result = await process_dataframe(df_chunk, file.filename)
            
            # Update tracking
            batch_tracker.add(batch_num)
            processed_df = pd.concat([processed_df, batch_result], ignore_index=True)
            
            # Save current state
            processed_df.to_excel(output_filename, index=False)

            # Yield batch result with unique identifier
            yield json.dumps({
                "id": f"batch_{batch_num + 1}_{int(time.time() * 1000)}",  # Add unique timestamp
                "batch": batch_num + 1,
                "total_batches": total_batches,
                "message": f"Processing Batch: {batch_num + 1}/{total_batches}",
                "batch_result": batch_result.to_dict(orient='records')
            }) + "\n"

        # Generate plot only once at the end
        if len(processed_df) > 0:
            plot_image(processed_df)
            yield json.dumps({
                "id": f"complete_{int(time.time() * 1000)}",
                "message": "Processing complete. Plot generated and file saved."
            }) + "\n"

    return StreamingResponse(
        stream_batches(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

@app.get("/downloadfile/{filename}")
async def download_file(filename: str):
    file_location = os.path.join(UPLOAD_DIRECTORY, filename)
    if not os.path.exists(file_location):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        file_location,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=filename,
    )

@app.get("/plot")
async def get_plot():
    """Serve the generated plot image."""
    plot_path = os.path.join(UPLOAD_DIRECTORY, "plot.png")
    if not os.path.exists(plot_path):
        raise HTTPException(status_code=404, detail="Plot not found")
    return FileResponse(plot_path)

@app.get("/files/")
async def list_files():
    """List all uploaded files."""
    files = os.listdir(UPLOAD_DIRECTORY)
    return {"files": files}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,  # Enable auto-reload
        reload_dirs=["./"]  # Watch current directory for changes
    )
