document.addEventListener('dblclick', function (event) {
  event.preventDefault();
});

// Normalize artist names for searching (e.g., "The Beatles" -> "Beatles, The")
function normalizeArtist(artist) {
  const theMatch = artist.match(/^The\s(.+)/i);
  return theMatch ? `${theMatch[1]}, The` : artist;
}

// Load the song data
fetch('songs.json')
  .then(response => response.json())
  .then(data => {
    const songs = processData(data); // Process data once
    setupSearch(songs); // Pass processed songs to setupSearch
    setupAlphabetBrowse(data);
  })
  .catch(error => console.error('Error loading JSON:', error));

// Function to process data into a searchable array
function processData(data) {
  const songs = [];
  for (const artist in data) {
    const normalizedArtist = normalizeArtist(artist); // Normalize artist
    data[artist].forEach(title => {
      songs.push({
        artist: normalizedArtist,
        title: title,
        combined: `${normalizedArtist} ${title}` // Combined field for better search
      });
    });
  }
  return songs; // Return the processed array
}

// Set up Fuse.js search
function setupSearch(songs) {
  const options = {
    keys: ['combined'], // Search by artist, title, and combined fields
    threshold: 0.4, // Adjust sensitivity
    distance: 100, // Allow partial matches across words
    includeScore: true,
  };
  const fuse = new Fuse(songs, options);

  // Handle search input
  const searchInput = document.getElementById('searchInput');
  const resultsList = document.getElementById('resultsList');

  function debounce(func, delay) {
    let timeout;
    return function (...args) {
      clearTimeout(timeout);
      timeout = setTimeout(() => func.apply(this, args), delay);
    };
  }

  searchInput.addEventListener('input', debounce(() => {
    const query = searchInput.value.trim().toLowerCase();
    const results = fuse.search(query);
    resultsList.innerHTML = '';
    // Limit the number of results displayed to 50
    const maxResultsToDisplay = 50;
    const resultsToDisplay = results.slice(0, maxResultsToDisplay);
    if (resultsToDisplay.length > 0) {
      resultsToDisplay.forEach(result => {
        const li = document.createElement('li');
        li.textContent = `${result.item.artist} - ${result.item.title}`;
        resultsList.appendChild(li);
      });
      // If there are more than 100 results, indicate that more are available
      if (results.length > maxResultsToDisplay) {
        const li = document.createElement('li');
        li.textContent = `And ${results.length - maxResultsToDisplay} more...`;
        resultsList.appendChild(li);
      }
    } else {
      const li = document.createElement('li');
      li.textContent = 'No results found';
      resultsList.appendChild(li);
    }
  }, 600));
}


// Set up alphabet browse functionality
function setupAlphabetBrowse(data) {
  const alphabet = '+0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('');
  const alphabetDropdown = document.getElementById('alphabetDropdown');
  const artistList = document.getElementById('artistList');
  const songList = document.getElementById('songList');
  const closeSongList = document.getElementById('closeSongList');
  const songListHeader = document.getElementById('songListHeader');
  const artistNameElem = document.getElementById('artistName');
  const paginationControls =  document.getElementById('paginationControls')
  const itemsPerPage = getColumnCount() * 7; // Number of artists to display per page
  let currentPage = 1; // Track the current page

  // Create alphabet dropdown options
  alphabet.forEach(letter => {
    const option = document.createElement('option');
    option.value = letter;
    option.textContent = letter;
    alphabetDropdown.appendChild(option);
  });

  // Handle dropdown change
  alphabetDropdown.addEventListener('change', (event) => {
    const selectedLetter = event.target.value;
    if (selectedLetter) {
      currentPage = 1; // Reset to first page when a new letter is selected
      displayArtistsByLetter(selectedLetter);
    }
  });

  // Start on page 'A'
  alphabetDropdown.value = 'A';
  displayArtistsByLetter('A');


  // Display artists when a letter is clicked
  function displayArtistsByLetter(letter) {
    artistList.innerHTML = ''; // Clear previous artists
    songList.innerHTML = ''; // Clear previous song lists
    songListHeader.style.display = 'none'; // Hide the song list header
    paginationControls.style.display = 'block';
    artistList.style.display = 'block';
    // Filter and display artists starting with the selected letter
    const artists = Object.keys(data).filter(artist => normalizeArtist(artist)[0].toUpperCase() === letter);

    // Handle if no artists with that letter
    if (artists.length === 0) {
      artistList.innerHTML = `<div class="no-artists">No artists found under ${letter}</div>`;
      return;
    }

    const totalPages = Math.ceil(artists.length / itemsPerPage);
    displayArtists(artists);
    createPaginationControls(totalPages, artists);
  }

  // Create pagination controls
  function createPaginationControls(totalPages, artists) {
    const paginationControls = document.getElementById('paginationControls');
    paginationControls.innerHTML = ''; // Clear previous controls

    // Previous button
    const prevButton = document.createElement('button');
    prevButton.classList.add('pagination-button');
    prevButton.textContent = 'Previous';
    prevButton.disabled = currentPage === 1;
    prevButton.addEventListener('click', () => {
      if (currentPage > 1) {
        currentPage--; // Update the current page
        displayArtists(artists); // Refresh the artist display
        updateCurrentPageDisplay(currentPage, totalPages);
        prevButton.disabled = currentPage === 1; // Disable if on first page
        nextButton.disabled = currentPage === totalPages; // Enable/disable next button
      }
    });
    paginationControls.appendChild(prevButton);

    // Current page
    const currentPageElem = document.createElement('span');
    currentPageElem.id = 'current-page';
    currentPageElem.textContent = `Page ${currentPage} of ${totalPages}`;
    paginationControls.appendChild(currentPageElem);

    // Next button
    const nextButton = document.createElement('button');
    nextButton.classList.add('pagination-button');
    nextButton.textContent = 'Next';
    nextButton.disabled = currentPage === totalPages;
    nextButton.addEventListener('click', () => {
      if (currentPage < totalPages) {
        currentPage++; // Update the current page
        displayArtists(artists); // Refresh the artist display
        updateCurrentPageDisplay(currentPage, totalPages);
        prevButton.disabled = currentPage === 1; // Enable/disable previous button
        nextButton.disabled = currentPage === totalPages; // Enable/disable next button
      }
    });
    paginationControls.appendChild(nextButton);
  }


  // Function to update current page display
  function updateCurrentPageDisplay(currentPage, totalPages) {
    const currentPageElem = document.getElementById('current-page');
    currentPageElem.textContent = `Page ${currentPage} of ${totalPages}`;
  }

  // Function to get the column count based on screen width
  function getColumnCount() {
    const width = window.innerWidth;
    if (width <= 768) { // Adjust the breakpoint as needed for mobile
      return 2; // Use 2 columns on mobile
    } else {
      return 5; // Use 5 columns on larger screens
    }
  }

  // Function to display artists based on the current page in a multi-column layout
  function displayArtists(artists) {
    artistList.innerHTML = ''; // Clear any previous artists
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = Math.min(startIndex + itemsPerPage, artists.length);
    const artistsToShow = artists.slice(startIndex, endIndex);

    const columnCount = getColumnCount(); // Number of columns
    const columnWrapper = document.createElement('div');
    columnWrapper.classList.add('artist-column-wrapper'); // Added class for styling
    columnWrapper.style.display = 'grid';
    columnWrapper.style.gridTemplateColumns = `repeat(${columnCount}, 1fr)`;
    columnWrapper.style.gap = '5px'; // Gap between columns

    artistsToShow.forEach(artist => {
      const normalizedArtist = normalizeArtist(artist);
      const artistItem = document.createElement('div');
      artistItem.classList.add('artist-item');
      artistItem.textContent = normalizedArtist;
      artistItem.style.cursor = 'pointer';
      artistItem.addEventListener('click', () => {
        displaySongsByArtist(normalizedArtist, data[artist]);
      });
      columnWrapper.appendChild(artistItem);
    });

    artistList.appendChild(columnWrapper);
  }


// Event listener for hiding song list and song list header
closeSongList.addEventListener('click', function () {
  // Hide the song list and the song list header
  songList.style.display = 'none';
  songListHeader.style.display = 'none';

  // Show the artist list and pagination controls
  artistList.style.display = 'block';
  paginationControls.style.display = 'block';
});

// Display songs when an artist is clicked
function displaySongsByArtist(artist, songs) {
  songList.innerHTML = ''; // Clear previous songs
  artistNameElem.textContent = artist; // Update artist name in the header
  songListHeader.style.display = 'block'; // Show the song list header
  songList.style.display = 'block';

  paginationControls.style.display = 'none'; // Hide pagination controls
  artistList.style.display = 'none'; // Hide artist list

  // Populate the song list
  songs.forEach(song => {
    const li = document.createElement('li');
    li.classList.add('song-item'); // Added class for styling
    li.textContent = song;
    songList.appendChild(li);
  });
}



}
