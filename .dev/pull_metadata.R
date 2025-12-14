pacman::p_load(
  stringr,
  httr,
  jsonlite,
  dplyr,
  GET
)

# Source helper functions
paths <- list.files('3_functions/', full.names = TRUE)
lapply(paths, source)
rm(paths)

# Define function
pull_metadata <- function(base_url,
                          type = c('file', 'dataset', 'dataverse'),
                          per_page = 1000,
                          page_limit = 10) {

  # Base URL that can take arguments with glue
  base_url <- paste0(base_url, '/api/search?q=*&type={type}&per_page={per_page}&start={start}')

  # Starting parameters
  start <- 0
  page_num <- 1
  condition <- TRUE

  # Data frame for results
  results <- data.frame()

  # While based on condition but also back-up stop: page limit
  while(condition && page_num <= page_limit) {

    # Make url based on start value
    url <- str_glue(base_url)
    cat('\nQuery:', url)

    # Pull metadata from url, format, and remove some cols we don't need
    page_result <- get(url)

    # Clean based on type of file
    if (type == 'file') {
      page_result <- page_result %>%
        clean_files_page()
    } else if (type == 'dataset' | type == 'dataverse') {
      page_result <- page_result %>%
        clean_page()
    }

    # Bind new page into previous results
    results <- bind_rows(results, page_result)

    # Increase start value, page ticker
    start <- start + nrow(page_result)
    page_num <- page_num + 1

    # If the page result capped out the per_page limit, continue while loop
    condition <- nrow(page_result) == per_page
  }
  return(results)
}


