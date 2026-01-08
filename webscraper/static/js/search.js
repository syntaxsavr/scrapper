document.addEventListener('DOMContentLoaded', function() {
    const searchForm = document.getElementById('search-form');
    const searchInput = document.getElementById('search-input');
    const resultsContainer = document.getElementById('results-container');

    if (!searchForm || !searchInput || !resultsContainer) {
        return;
    }

    let isAuthenticated = false; // Track if user is logged in

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
                // Check if this is a duplicate scrape (for logged-in users)
                if (data.status === 'duplicate' && data.existing) {
                    resultsContainer.innerHTML =
                        '<div class="content">' +
                        '<div style="background: #fff3cd; border: 1px solid #ffc107; padding: 20px; border-radius: 8px; margin: 20px 0;">' +
                        '<h3 style="color: #856404; margin-top: 0;"><i class="fas fa-exclamation-triangle"></i> Duplicate Search</h3>' +
                        '<p style="color: #856404;">' + escapeHtml(data.message) + '</p>' +
                        '<div style="margin-top: 15px;">' +
                        '<a href="/scrapes/' + data.scrape_id + '/" class="btn btn-primary" style="text-decoration: none; display: inline-block; padding: 10px 20px; background: #007bff; color: white; border-radius: 4px;">' +
                        '<i class="fas fa-eye"></i> View Existing Scrape' +
                        '</a>' +
                        '<button onclick="location.reload()" class="btn btn-secondary" style="margin-left: 10px; padding: 10px 20px; background: #6c757d; color: white; border: none; border-radius: 4px; cursor: pointer;">' +
                        '<i class="fas fa-redo"></i> Search Again Anyway' +
                        '</button>' +
                        '</div>' +
                        '</div>' +
                        '</div>';
                    return;
                }

                const taskIds = data.task_ids;
                const primaryTaskId = taskIds[0];
                isAuthenticated = data.is_authenticated || false; // Store auth status
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
        let displayedResults = []; // Track what we've already displayed
        let isLoading = true; // Track if still loading

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
                        console.log('Status response:', JSON.stringify(statusData, null, 2)); // DEBUG
                        if (statusData.status === 'completed') {
                            primaryComplete = true;
                            // Check if results exist
                            if (statusData.results && Array.isArray(statusData.results)) {
                                console.log('Primary search complete. Found', statusData.results.length, 'results');
                                // Display results progressively
                                displayResultsProgressively(query, statusData.results, displayedResults, scrapingTaskIds.length > 0 || retriggeredTaskIds.length > 0);
                            } else {
                                console.error('No results array in statusData:', statusData);
                                // Still display with empty results
                                displayResultsProgressively(query, [], displayedResults, scrapingTaskIds.length > 0 || retriggeredTaskIds.length > 0);
                            }
                            return { completed: true };
                        } else if (statusData.status === 'failed') {
                            primaryComplete = true;
                            resultsContainer.innerHTML =
                                '<div class="content">' +
                                '<p class="error">Search failed: ' + (statusData.error || 'Unknown error') + '</p>' +
                                '</div>';
                            return { completed: true };
                        } else {
                            // Show loading state
                            if (displayedResults.length === 0) {
                                resultsContainer.innerHTML =
                                    '<div class="content">' +
                                    '<h2>Searching for "' + escapeHtml(query) + '"...</h2>' +
                                    '<div class="loading-spinner" style="text-align: center; padding: 40px;">' +
                                    '<i class="fas fa-spinner fa-spin" style="font-size: 48px; color: #007bff;"></i>' +
                                    '<p style="margin-top: 15px; color: #666; font-size: 16px;">Finding datasets...</p>' +
                                    '</div>' +
                                    '</div>';
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
                            // Display new results progressively
                            displayResultsProgressively(query, statusData.results, displayedResults, scrapingTaskIds.length > 0);
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

    function displayResultsProgressively(query, newResults, displayedResults, stillLoading) {
        console.log('displayResultsProgressively called with', newResults.length, 'new results');
        console.log('Current displayedResults count:', displayedResults.length);
        
        // Limit to 100 total results
        const allResults = newResults.slice(0, 100);
        
        // Find new results that haven't been displayed yet
        const newUnseenResults = allResults.filter(function(result) {
            return !displayedResults.some(function(displayed) {
                return displayed.id === result.id;
            });
        });
        
        console.log('Found', newUnseenResults.length, 'new unseen results');
        
        // Add new results to displayed list
        newUnseenResults.forEach(function(result) {
            if (displayedResults.length < 100) {
                displayedResults.push(result);
            }
        });
        
        console.log('Total displayedResults after adding:', displayedResults.length);
        
        // Build the HTML
        let html = '<div class="content">';
        
        // Header with result count and Add to Scrapes button
        html += '<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">';
        
        // Adjust text if exactly 100 results (likely more available)
        if (displayedResults.length === 100 && !stillLoading) {
            html += '<h2>Displaying first 100 results for "' + escapeHtml(query) + '"</h2>';
        } else {
            html += '<h2>Found ' + displayedResults.length + ' result(s) for "' + escapeHtml(query) + '"';
            if (stillLoading) {
                html += ' <i class="fas fa-spinner fa-spin" style="font-size: 20px; color: #007bff; margin-left: 10px;"></i>';
            }
            html += '</h2>';
        }
        
        // Show "Add to Scrapes" button if user is logged in
        if (isAuthenticated) {
            html += '<button id="add-to-scrapes-btn" class="btn btn-primary" style="padding: 10px 20px; background: #28a745; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 14px;">' +
                    '<i class="fas fa-plus"></i> Add to My Scrapes' +
                    '</button>';
        }
        html += '</div>';
        
        // Show loading indicator if still searching
        if (stillLoading) {
            html += '<p style="color: #007bff; background: #e7f3ff; padding: 10px; border-radius: 4px; margin-bottom: 15px;">' +
                    '<i class="fas fa-sync fa-spin"></i> Still searching for more results...' +
                    '</p>';
        }
        
        // Show notification if results are limited
        if (allResults.length > 100) {
            html += '<p style="color: #856404; background: #fff3cd; padding: 10px; border-radius: 4px; margin-bottom: 15px;">' +
                    '<i class="fas fa-info-circle"></i> Showing first 100 of ' + allResults.length + ' results' +
                    '</p>';
        }
        
        if (displayedResults.length === 0) {
            if (stillLoading) {
                html += '<div class="loading-spinner" style="text-align: center; padding: 40px;">' +
                        '<i class="fas fa-spinner fa-spin" style="font-size: 48px; color: #007bff;"></i>' +
                        '<p style="margin-top: 15px; color: #666; font-size: 16px;">Finding datasets...</p>' +
                        '</div>';
            } else {
                html += '<h2>No results found for "' + escapeHtml(query) + '"</h2>' +
                        '<p>Try a different search term.</p>';
            }
        } else {
            // Add filter input
            html += '<div class="results-filter">';
            html += '<input type="text" id="results-filter-input" placeholder="🔍 Filter results by title, description, author, or tags..." />';
            html += '</div>';
            
            html += '<div class="results-list" id="results-list">';

            displayedResults.forEach(function(result, index) {
                html += '<a href="/detailed_view/' + result.id + '/" class="result-link" data-result-index="' + index + '" data-result-title="' + escapeHtml(result.title || '').toLowerCase() + '" data-result-desc="' + escapeHtml(result.description || '').toLowerCase() + '" data-result-author="' + escapeHtml(result.author || '').toLowerCase() + '" data-result-tags="' + escapeHtml(result.tags || '').toLowerCase() + '">';
                html += '<div class="result-item" style="animation: fadeIn 0.3s ease-in;">';
                
                // Title with source badge
                html += '<div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px; flex-wrap: wrap;">';
                html += '<h3 style="margin: 0; flex: 1;">' + escapeHtml(result.title) + '</h3>';
                if (result.source && result.source !== 'unknown') {
                    const sourceBadgeColor = result.source === 'huggingface' ? '#FFD21E' : '#20BEFF';
                    const sourceBadgeIcon = result.source === 'huggingface' ? '🤗' : '📊';
                    const sourceName = result.source === 'huggingface' ? 'HuggingFace' : 'Kaggle';
                    html += '<span style="background: ' + sourceBadgeColor + '; color: #000; padding: 4px 10px; border-radius: 4px; font-size: 12px; font-weight: bold; white-space: nowrap;">' +
                            sourceBadgeIcon + ' ' + sourceName + '</span>';
                }
                html += '</div>';
                
                // Description with truncation
                if (result.description) {
                    const maxLength = 200;
                    const desc = result.description.length > maxLength 
                        ? result.description.substring(0, maxLength) + '...' 
                        : result.description;
                    html += '<p>' + escapeHtml(desc) + '</p>';
                }
                
                // Meta information
                html += '<div class="result-meta">';
                if (result.author) {
                    html += '<span><i class="fas fa-user"></i> ' + escapeHtml(result.author) + '</span>';
                }
                if (result.downloads && result.downloads > 0) {
                    html += '<span><i class="fas fa-download"></i> ' + formatNumber(result.downloads) + '</span>';
                }
                if (result.likes && result.likes > 0) {
                    html += '<span><i class="fas fa-heart"></i> ' + formatNumber(result.likes) + '</span>';
                }
                html += '</div>';
                
                // Tags
                if (result.tags) {
                    const tagsArray = result.tags.split(',').map(function(t) { return t.trim(); }).filter(function(t) { return t; });
                    if (tagsArray.length > 0) {
                        html += '<div class="result-tags">';
                        tagsArray.slice(0, 5).forEach(function(tag) {
                            html += '<span class="tag">' + escapeHtml(tag) + '</span>';
                        });
                        if (tagsArray.length > 5) {
                            html += '<span class="tag">+' + (tagsArray.length - 5) + ' more</span>';
                        }
                        html += '</div>';
                    }
                }
                
                html += '</div>';
                html += '</a>';
            });

            html += '</div>';
        }
        
        html += '</div>';
        resultsContainer.innerHTML = html;

        // Add event listener to "Add to Scrapes" button
        if (isAuthenticated) {
            const addBtn = document.getElementById('add-to-scrapes-btn');
            if (addBtn) {
                addBtn.addEventListener('click', function() {
                    addToScrapes(query, addBtn);
                });
            }
        }
        
        // Add filter functionality
        const filterInput = document.getElementById('results-filter-input');
        if (filterInput) {
            filterInput.addEventListener('input', function() {
                filterResults(this.value);
            });
        }
        
        // Scroll to show newly added results (only if not first load)
        if (newUnseenResults.length > 0 && displayedResults.length > newUnseenResults.length) {
            const resultsList = document.getElementById('results-list');
            if (resultsList && resultsList.lastElementChild) {
                resultsList.lastElementChild.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
        }
    }

    function displayResults(query, statusData) {
        // Limit to 100 results for performance
        const results = statusData.results || []; // Handle missing results
        const limitedResults = results.slice(0, 100);

        if (limitedResults.length === 0) {
            resultsContainer.innerHTML =
                '<div class="content">' +
                '<h2>No results found for "' + escapeHtml(query) + '"</h2>' +
                '<p>Try a different search term.</p>' +
                '</div>';
        } else {
            let html = '<div class="content">';
            
            // Header with result count and Add to Scrapes button
            html += '<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">';
            html += '<h2>Found ' + limitedResults.length + ' result(s) for "' + escapeHtml(query) + '"</h2>';
            
            // Show "Add to Scrapes" button if user is logged in
            if (isAuthenticated) {
                html += '<button id="add-to-scrapes-btn" class="btn btn-primary" style="padding: 10px 20px; background: #28a745; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 14px;">' +
                        '<i class="fas fa-plus"></i> Add to My Scrapes' +
                        '</button>';
            }
            html += '</div>';
            
            // Show notification if results are limited
            if (results.length > 100) {
                html += '<p style="color: #856404; background: #fff3cd; padding: 10px; border-radius: 4px; margin-bottom: 15px;">' +
                        '<i class="fas fa-info-circle"></i> Showing first 100 of ' + results.length + ' results' +
                        '</p>';
            }
            
            html += '<div class="results-list">';

            limitedResults.forEach(function(result) {
                html += '<a href="/detailed_view/' + result.id + '/" class="result-link">';
                html += '<div class="result-item">';
                html += '<h3>' + escapeHtml(result.title) + '</h3>';
                html += '<p>' + escapeHtml(result.description) + '</p>';
                html += '</div>';
                html += '</a>';
            });

            html += '</div></div>';
            resultsContainer.innerHTML = html;

            // Add event listener to "Add to Scrapes" button
            if (isAuthenticated) {
                const addBtn = document.getElementById('add-to-scrapes-btn');
                if (addBtn) {
                    addBtn.addEventListener('click', function() {
                        addToScrapes(query, addBtn);
                    });
                }
            }
        }
    }

    function addToScrapes(query, button) {
        // Disable button and show loading state
        button.disabled = true;
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Adding...';

        fetch('/api/create-scrape/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ query: query })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                // Success - show success message and link to scrape
                button.innerHTML = '<i class="fas fa-check"></i> Added!';
                button.style.background = '#28a745';
                
                // Show notification with link to scrape
                const notification = document.createElement('div');
                notification.style.cssText = 'position: fixed; top: 20px; right: 20px; background: #28a745; color: white; padding: 15px 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); z-index: 1000;';
                notification.innerHTML = 
                    '<strong><i class="fas fa-check-circle"></i> Scrape added successfully!</strong><br>' +
                    '<a href="/scrapes/' + data.scrape_id + '/" style="color: white; text-decoration: underline;">View scrape</a>';
                document.body.appendChild(notification);
                
                setTimeout(function() {
                    notification.remove();
                }, 5000);
            } else if (data.status === 'duplicate') {
                // Duplicate - show link to existing scrape
                button.innerHTML = '<i class="fas fa-info-circle"></i> Already exists';
                button.style.background = '#ffc107';
                
                const notification = document.createElement('div');
                notification.style.cssText = 'position: fixed; top: 20px; right: 20px; background: #ffc107; color: #000; padding: 15px 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); z-index: 1000;';
                notification.innerHTML = 
                    '<strong><i class="fas fa-exclamation-triangle"></i> ' + escapeHtml(data.message) + '</strong><br>' +
                    '<a href="/scrapes/' + data.scrape_id + '/" style="color: #000; text-decoration: underline;">View existing scrape</a>';
                document.body.appendChild(notification);
                
                setTimeout(function() {
                    notification.remove();
                    button.disabled = false;
                    button.innerHTML = '<i class="fas fa-plus"></i> Add to My Scrapes';
                    button.style.background = '#28a745';
                }, 5000);
            }
        })
        .catch(error => {
            console.error('Error adding to scrapes:', error);
            button.disabled = false;
            button.innerHTML = '<i class="fas fa-exclamation-circle"></i> Error';
            button.style.background = '#dc3545';
            
            setTimeout(function() {
                button.innerHTML = '<i class="fas fa-plus"></i> Add to My Scrapes';
                button.style.background = '#28a745';
            }, 3000);
        });
    }

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    function filterResults(searchTerm) {
        const term = searchTerm.toLowerCase();
        const resultLinks = document.querySelectorAll('.result-link');
        let visibleCount = 0;
        
        resultLinks.forEach(function(link) {
            const title = link.getAttribute('data-result-title') || '';
            const desc = link.getAttribute('data-result-desc') || '';
            const author = link.getAttribute('data-result-author') || '';
            const tags = link.getAttribute('data-result-tags') || '';
            
            const matches = title.includes(term) || desc.includes(term) || 
                          author.includes(term) || tags.includes(term);
            
            if (matches) {
                link.style.display = 'block';
                visibleCount++;
            } else {
                link.style.display = 'none';
            }
        });
        
        // Update results count in header
        const resultsHeader = document.querySelector('.content h2');
        if (resultsHeader && searchTerm) {
            const totalResults = resultLinks.length;
            // Store original text if not already stored
            if (!resultsHeader.dataset.originalText) {
                resultsHeader.dataset.originalText = resultsHeader.textContent;
            }
            // Remove any existing spinner
            const spinnerIndex = resultsHeader.textContent.indexOf(' result(s)');
            if (spinnerIndex > 0) {
                const baseText = resultsHeader.textContent.substring(0, spinnerIndex + 10);
                resultsHeader.innerHTML = 'Showing ' + visibleCount + ' of ' + totalResults + ' results';
            }
        } else if (resultsHeader && resultsHeader.dataset.originalText) {
            resultsHeader.innerHTML = resultsHeader.dataset.originalText;
        }
    }
    
    function formatNumber(num) {
        if (num >= 1000000) {
            return (num / 1000000).toFixed(1) + 'M';
        } else if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        }
        return num.toString();
    }
});
