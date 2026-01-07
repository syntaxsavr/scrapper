document.addEventListener('DOMContentLoaded', function() {
    const searchForm = document.getElementById('search-form');
    const searchInput = document.getElementById('search-input');
    const resultsContainer = document.getElementById('results-container');

    if (!searchForm || !searchInput || !resultsContainer) {
        return;
    }

    searchForm.addEventListener('submit', function(event) {
        event.preventDefault();

        const query = searchInput.value.trim();

        if (!query) {
            resultsContainer.innerHTML =
                '<p class="error">Please enter a search term.</p>';
            return;
        }

        resultsContainer.innerHTML =
            '<div class="content"><h2>Searching for "' + escapeHtml(query) + '"...</h2></div>';

        startSearch(query);
    });

    function startSearch(query) {
        fetch('/api/search/?q=' + encodeURIComponent(query))
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                const taskIds = data.task_ids;
                const primaryTaskId = taskIds[0];
                console.log('Search tasks started:', taskIds);

                pollMultipleTasks(taskIds, primaryTaskId, query);
            })
            .catch(error => {
                console.error('Error starting search:', error);
                resultsContainer.innerHTML =
                    '<div class="content">' +
                    '<p class="error">Error starting search. Please try again.</p>' +
                    '</div>';
            });
    }

    function pollMultipleTasks(taskIds, primaryTaskId, query) {
        let primaryComplete = false;
        let scrapingTaskIds = taskIds.filter(function(id) { return id !== primaryTaskId; });
        let retriggeredTaskIds = [];
        let hasDisplayedResults = false; // Track if we've shown any results

        let currentDelay = 500;
        const minDelay = 500;
        const maxDelay = 8000;
        const backoffMultiplier = 1.5;

        function resetDelay() {
            currentDelay = minDelay;
        }

        function increaseDelay() {
            currentDelay = Math.min(currentDelay * backoffMultiplier, maxDelay);
        }

        async function pollTasks() {
            const fetchPromises = [];
            const completedScrapingTaskIds = [];
            const completedRetriggerTaskIds = [];
            const newRetriggerTaskIds = [];

            if (!primaryComplete) {
                const primaryPromise = fetch('/api/status/' + primaryTaskId + '/')
                    .then(response => response.json())
                    .then(statusData => {
                        if (statusData.status === 'completed') {
                            primaryComplete = true;
                            console.log('Primary search complete. Found', statusData.results.length, 'results');
                            
                            // Check if we have active scraping/retrigger tasks
                            const stillSearching = scrapingTaskIds.length > 0 || retriggeredTaskIds.length > 0;
                            displayResults(query, statusData, stillSearching);
                            hasDisplayedResults = true;
                            return { completed: true };
                        } else {
                            // Only show "Searching..." if we haven't displayed results yet
                            if (!hasDisplayedResults) {
                                resultsContainer.innerHTML =
                                    '<div class="content"><h2>Searching...</h2></div>';
                            }
                            return { completed: false };
                        }
                    })
                    .catch(error => {
                        console.error('Error checking primary task:', error);
                        return { completed: false };
                    });
                fetchPromises.push(primaryPromise);
            }

            scrapingTaskIds.forEach(function(taskId) {
                const scrapingPromise = fetch('/api/status/' + taskId + '/')
                    .then(response => response.json())
                    .then(statusData => {
                        if (statusData.status === 'completed') {
                            completedScrapingTaskIds.push(taskId);

                            if (statusData.retrigger_task_id) {
                                console.log('Scraping complete. New retrigger task:', statusData.retrigger_task_id);
                                newRetriggerTaskIds.push(statusData.retrigger_task_id);
                            }
                            return { completed: true };
                        }
                        return { completed: false };
                    })
                    .catch(error => {
                        console.error('Error checking scraping task:', error);
                        return { completed: false };
                    });
                fetchPromises.push(scrapingPromise);
            });

            retriggeredTaskIds.forEach(function(retriggerTaskId) {
                const retriggerPromise = fetch('/api/status/' + retriggerTaskId + '/')
                    .then(response => response.json())
                    .then(statusData => {
                        if (statusData.status === 'completed' && statusData.results) {
                            console.log('Retrigger complete. Updated results:', statusData.results.length);
                            
                            // Check if we still have scraping tasks running
                            const stillSearching = scrapingTaskIds.length > 0;
                            displayResults(query, statusData, stillSearching);
                            hasDisplayedResults = true;
                            completedRetriggerTaskIds.push(retriggerTaskId);
                            return { completed: true };
                        }
                        return { completed: false };
                    })
                    .catch(error => {
                        console.error('Error checking retrigger task:', error);
                        return { completed: false };
                    });
                fetchPromises.push(retriggerPromise);
            });

            const results = await Promise.all(fetchPromises);

            scrapingTaskIds = scrapingTaskIds.filter(function(id) {
                return completedScrapingTaskIds.indexOf(id) === -1;
            });

            retriggeredTaskIds = retriggeredTaskIds.filter(function(id) {
                return completedRetriggerTaskIds.indexOf(id) === -1;
            });

            newRetriggerTaskIds.forEach(function(taskId) {
                if (retriggeredTaskIds.indexOf(taskId) === -1) {
                    retriggeredTaskIds.push(taskId);
                }
            });

            if (primaryComplete && scrapingTaskIds.length === 0 && retriggeredTaskIds.length === 0) {
                console.log('All tasks complete');
                return;
            }

            const anyTaskCompleted = results.some(function(result) { return result.completed; });

            if (anyTaskCompleted) {
                resetDelay();
            } else {
                increaseDelay();
            }

            console.log('Next poll in ' + currentDelay + 'ms');
            setTimeout(pollTasks, currentDelay);
        }

        pollTasks();
    }

    function displayResults(query, statusData, stillSearching) {
        if (statusData.results.length === 0) {
            if (stillSearching) {
                // Still searching, show a waiting message with spinner or indication
                resultsContainer.innerHTML =
                    '<div class="content">' +
                    '<h2>Searching for more results...</h2>' +
                    '<p>Currently found 0 results. Checking additional sources...</p>' +
                    '</div>';
            } else {
                // All tasks complete, truly no results
                resultsContainer.innerHTML =
                    '<div class="content">' +
                    '<h2>No results found for "' + escapeHtml(query) + '"</h2>' +
                    '<p>Try a different search term.</p>' +
                    '</div>';
            }
        } else {
            let html = '<div class="content">';
            html += '<h2>Found ' + statusData.results.length + ' result(s) for "' + escapeHtml(query) + '"</h2>';
            
            // Show "searching for more" indicator if still active
            if (stillSearching) {
                html += '<p style="color: #666; font-style: italic;">Searching for more results...</p>';
            }
            
            html += '<div class="results-list">';

            statusData.results.forEach(function(result) {
                html += '<a href="/detailed_view/' + result.id + '/" class="result-link">';
                html += '<div class="result-item">';
                html += '<h3>' + escapeHtml(result.title) + '</h3>';
                html += '<p>' + escapeHtml(result.description) + '</p>';
                html += '</div>';
                html += '</a>';
            });

            html += '</div></div>';
            resultsContainer.innerHTML = html;
        }
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
});
