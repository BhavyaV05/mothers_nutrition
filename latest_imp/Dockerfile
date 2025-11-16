# Use an official Python 3.11 slim image as the base
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file first to leverage Docker cache
COPY requirements.txt .

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create the upload folder that the app needs
# The -p flag ensures it doesn't error if the folder exists
RUN mkdir -p /app/uploads

# Copy the rest of your application code into the container
COPY . .

# Expose the port the app will run on
EXPOSE 5000

# Define the command to run your application using Gunicorn
# This tells Gunicorn to run the 'app' object from the 'app.py' file
# It binds to 0.0.0.0:5000, making it accessible from outside the container
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]