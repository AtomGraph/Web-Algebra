# Cities in Denmark

Take "Select 10 biggest cities in Denmark as well as their names (?city ?cityName)" as the question and query their titles and descriptions using SPARQL from [DBpedia's endpoint](https://dbpedia.org/sparql). For each of the cities, create a document with a unique URL relative to https://localhost:4443/denmark/ and write the respective city metadata into them. Make sure the new document URLs are formatted with a trailing slash (`https://localhost:4443/denmark/${cityName}/`).

# Complex Natural Language Queries for Knowledge Graph Processing  

## 1. Nobel Prize Laureates and Their Countries  
Find all Nobel Prize winners in Physics from the past 50 years, retrieving their names, birth countries, and short biographies from [Wikidata](https://query.wikidata.org/). For each laureate, create a dedicated profile page under https://localhost:4443/nobel/winners/, including their award details and nationality.  

---

## 2. AI Research Papers and Citation Networks  
Retrieve recent AI-related research papers from [OpenCitations](https://opencitations.net/sparql) and extract their **most frequently cited sources**. For each paper, generate a structured bibliographic record at https://localhost:4443/research/ai/, linking each paper to its referenced works.  

---

## 3. Film Directors and Their Most Notable Works  
Get a list of film directors from [DBpedia](https://dbpedia.org/sparql) along with their **three most acclaimed movies**. For each director, create an entry under https://localhost:4443/film/directors/ containing their biography and links to individual film profiles.  

---

## 4. Space Missions and Their Astronauts  
Fetch details about **all space missions since 2000** from [NASA’s Linked Data](https://data.nasa.gov/sparql), including the crew members for each mission. Create a mission report under https://localhost:4443/space/missions/, listing astronaut profiles and their associated missions.  

---

## 5. Classical Composers and Their Masterpieces  
Find **European classical composers** and their most frequently performed works using [Wikidata](https://query.wikidata.org/). For each composer, generate a profile under https://localhost:4443/music/composers/, including a list of compositions and links to available scores.  

---

## 6. Weather Observations from Global Stations  
Query [NOAA’s Linked Data](https://data.noaa.gov/) for **temperature readings** from the 10 coldest locations in the world over the past year. Store these observations under https://localhost:4443/weather/stations/, with a separate record for each station’s temperature trends.  

---

## 7. European Monarchs and Their Successors  
Retrieve **historical European monarchs** along with their successors from [Wikidata](https://query.wikidata.org/). For each ruler, create a detailed biography at https://localhost:4443/history/monarchs/, including lineage data and notable achievements.  

---

## 8. Ancient Philosophers and Their Teachings  
Find notable ancient philosophers from [Wikidata](https://query.wikidata.org/) along with **key ideas they influenced**. Create a knowledge archive at https://localhost:4443/philosophy/thinkers/, linking each philosopher to their works and intellectual legacy.  

---

## 9. Cities with the Fastest Population Growth  
Fetch data on **the fastest-growing cities worldwide** from [DBpedia](https://dbpedia.org/sparql), including their population trends over the past decade. For each city, generate an urban profile at https://localhost:4443/urban-growth/cities/, summarizing demographic shifts and economic factors.  

---

## 10. Scientific Discoveries and Their Impact  
Identify major scientific discoveries in **medicine and physics** from [Wikidata](https://query.wikidata.org/), along with key researchers and real-world applications. Create structured reports at https://localhost:4443/science/discoveries/, linking each discovery to its origin, contributors, and societal impact.  
