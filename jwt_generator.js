// jwt-generator.js
const fs = require('fs');
const KJUR = require('jsrsasign');
const cryptojs = require('crypto-js');
require('dotenv').config(); // Load environment variables from .env file

// Configuration - Update these values
const ACCOUNT_ID = process.env.ACCOUNT_ID;
if (!ACCOUNT_ID) {
    console.error("Error: ACCOUNT_ID not found in .env file");
    process.exit(1);
}
const CONSUMER_KEY = process.env.CONSUMER_KEY;
if (!CONSUMER_KEY) {
    console.error("Error: CONSUMER_KEY not found in .env file");
    process.exit(1);
}
const CERTIFICATE_ID = process.env.CERTIFICATE_ID;
if (!CERTIFICATE_ID) {
    console.error("Error: CERTIFICATE_ID not found in .env file");
    process.exit(1);
}
const PRIVATE_KEY_PATH = process.env.PRIVATE_KEY_PATH;
if (!PRIVATE_KEY_PATH) {
    console.error("Error: PRIVATE_KEY_PATH not found in .env file");
    process.exit(1);
}
const TOKEN_URL = `https://${ACCOUNT_ID}.suitetalk.api.netsuite.com/services/rest/auth/oauth2/v1/token`;

// Read private key
let privateKey;
try {
    privateKey = fs.readFileSync(PRIVATE_KEY_PATH, 'utf8');
} catch (error) {
    console.error(`Error reading private key: ${error.message}`);
    process.exit(1);
}

// Create JWT header
const jwtHeader = {
    alg: 'PS256', 
    typ: 'JWT',
    kid: CERTIFICATE_ID
};

// Stringify header
const stringifiedJwtHeader = JSON.stringify(jwtHeader);

// Create JWT payload
const now = Math.floor(Date.now() / 1000);  // Current time in seconds
const jwtPayload = {
    iss: CONSUMER_KEY,
    scope: ['restlets', 'rest_webservices'],
    iat: now,
    exp: now + 3600,  // 1 hour expiration
    aud: TOKEN_URL
};

// Stringify payload
const stringifiedJwtPayload = JSON.stringify(jwtPayload);

// Base64 encode the private key exactly as Postman does
const encodedSecret = cryptojs.enc.Base64.stringify(cryptojs.enc.Utf8.parse(privateKey));

// Sign the JWT with the PS256 algorithm using jsrsasign
// This is exactly how Postman does it: KJUR.jws.JWS.sign('PS256', stringifiedJwtHeader, stringifiedJwtPayload, secret)
const signedJWT = KJUR.jws.JWS.sign('PS256', stringifiedJwtHeader, stringifiedJwtPayload, privateKey);

// Output the JWT
console.log(signedJWT);