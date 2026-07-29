/* TESTING SENTIMENT ANALYSIS WITH AZURE OPENAI GPT OR AZURE AI LANGUAGE SERVICE */

/* 
    Testing before using the Azure OpenAI GPT model for sentiment analysis
    test the Azure OpenAI GPT model for sentiment analysis
    use this script to test the Azure OpenAI GPT model for sentiment analysis
    make sure to replace the placeholders with your actual Azure OpenAI details.
*/

/* ***************************************************************************
    PERFORM SENTIMENT ANALYSIS WITH AZURE OPENAI GPT FOR TESTING PURPOSES ONLY 
    ONCE THE MODEL IS TESTED THEN WE WILL PERFORM THE SENTIMENT ANALYSIS.
******************************************************************************/


-- 2) Call Azure OpenAI
EXEC sys.sp_invoke_external_rest_endpoint
    @method   = 'POST',
    @url      = 'https://<your azure openai name>.openai.azure.com/openai/deployments/<your deployment name>/chat/completions?api-version=<API_VERSION>',
    @headers  = '{"Content-Type":"application/json"}',
    @credential = [https://<your azure openai name>.openai.azure.com/],
    @payload  = @body,
    @response = @response OUTPUT;

-- 3) Extract the assistant's escaped JSON string
SELECT 
    @content = JSON_VALUE(@response, '$.result.choices[0].message.content');

-- 4) Unescape the JSON string so SQL can parse it
SELECT 
    @json = REPLACE(REPLACE(@content, '\"', '"'), '"{', '{');
SELECT 
    @json = REPLACE(@json, '}"', '}');

-- 5) Parse the clean JSON into fields
SELECT
    JSON_VALUE(@json, '$.feedback')          AS feedback,
    JSON_VALUE(@json, '$.sentiment_label')   AS sentiment_label,
    CAST(JSON_VALUE(@json, '$.positive_score') AS FLOAT) AS positive_score,
    CAST(JSON_VALUE(@json, '$.neutral_score')  AS FLOAT) AS neutral_score,
    CAST(JSON_VALUE(@json, '$.negative_score') AS FLOAT) AS negative_score,
    CAST(JSON_VALUE(@json, '$.mixed_score')    AS FLOAT) AS mixed_score;
GO


/* ***************************************************************************
            PERFORM SENTIMENT ANALYSIS WITH AZURE AI LANGUAGE SERVICE
                        FOR TESTING PURPOSES ONLY 
    ONCE THE MODEL IS TESTED THEN WE WILL PERFORM THE SENTIMENT ANALYSIS.
******************************************************************************/
--be aware: azure AI language service Summarization is no longer supported in API version 2023‑04‑01
--but we can use it for sentiment analysis
DECLARE @response NVARCHAR(MAX);

EXEC sys.sp_invoke_external_rest_endpoint
    @method = 'POST',
    @url = 'https://<your-az-ai-language-instance>.cognitiveservices.azure.com/language/:analyze-text?api-version=<your-api-version>',
    @headers = '{"Content-Type":"application/json","Ocp-Apim-Subscription-Key":"<your-api-key here>"}',
    @payload = N'{
        "kind": "SentimentAnalysis",
        "parameters": { "modelVersion": "latest" },
        "analysisInput": {
            "documents": [
                { "id": "1", "language": "en", "text": "Amazing sound quality..." }
            ]
        }
    }',
    @response = @response OUTPUT;

SELECT @response;
*/
DECLARE @response NVARCHAR(MAX);
DECLARE @content  NVARCHAR(MAX);
DECLARE @json     NVARCHAR(MAX);

-- 1) Build request with SYSTEM + USER messages
DECLARE @body NVARCHAR(MAX) = N'{
  "messages": [
    {
      "role": "system",
      "content": "You are a sentiment analysis engine. For the given text, return only a JSON object with the following fields: feedback (one concise summary sentence), sentiment_label (one of \"positive\", \"neutral\", \"negative\", \"mixed\"), positive_score, neutral_score, negative_score, mixed_score. All scores must be between 0 and 1 and sum to 1. Return no additional text."
    },
    {
      "role": "user",
      "content": "I love this demo"
    }
  ]
}';