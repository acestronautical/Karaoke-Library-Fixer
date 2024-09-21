# Karaoke Songbook

This project is a static website for managing karaoke song lists, allowing users to search and browse songs by artist. Note that this project will not work if index.html is opened directly due to CORS policy, this is normal.

## Prerequisites

- A GitHub account
- Git installed on your computer
- A songs.json with artist -> song list

## Instructions

1. **Create a GitHub Repository:**
   - Go to [GitHub](https://github.com).
   - Click the "+" icon in the upper right corner and select "New repository."
   - Name your repository (e.g., `my-website`), add a description, and choose "Public" or "Private."
   - Click "Create repository."

2. **Add Your Karaoke Name:**
   - Open index.html where it says `Change This to Your Karaoke Business Name` and replace Seattle Sound Entertainment with your Karaoke Business Name

3. **Open Your Terminal:**
   - Navigate to the directory where your "website" folder is located:
     ```bash
     cd path/to/your/website
     ```

   - Initialize a new Git repository:
     ```bash
     git init
     ```

   - Add all files in the "website" folder to the repository:
     ```bash
     git add .
     git commit -m "Initial commit"
     ```

4. **Push to GitHub:**
   - Follow the instructions for "push an existing repository from the command line" displayed on the repository page. They will be something like:
   ```bash
   git remote add origin https://github.com/yourusername/karaoke-songbook.git
   git branch -M main
   git push -u origin main
   ```

5. **Enable GitHub Pages:**
   - Go to your repository's **Settings**.
   - Select **Pages** from the sidebar.
   - Under **Source**, select the branch (usually `main`) and the root folder (`/`).
   - Click "Save."

Your karaoke songbook is now deployed and accessible via GitHub Pages and should be accessible at a url like `https://yourusername.github.io/yourrepositoryname/`
