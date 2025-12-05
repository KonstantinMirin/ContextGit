/**
 * Examples of contextgit metadata in JavaScript/TypeScript files.
 *
 * This file demonstrates the JSDoc format for embedding contextgit
 * metadata in JavaScript and TypeScript source files.
 */

// Example 1: Basic JSDoc block with @contextgit
// This is the recommended format

/**
 * Authenticate a user with username and password.
 *
 * @contextgit
 * id: C-017
 * type: code
 * title: Frontend Authentication
 * upstream: [SR-008]
 * status: active
 * tags: [auth, security, frontend]
 *
 * @param {string} username - The username
 * @param {string} password - The password
 * @returns {Promise<boolean>} Authentication result
 */
function authenticate(username, password) {
    return Promise.resolve(true);
}


// Example 2: React component with metadata

/**
 * User profile component.
 *
 * @contextgit
 * id: C-018
 * type: code
 * title: User Profile Component
 * upstream: [SR-009]
 * tags: [react, ui, profile]
 */
function UserProfile({ user }) {
    return <div>{user.name}</div>;
}


// Example 3: Class with metadata

/**
 * @contextgit
 * id: C-019
 * type: code
 * title: Data Service Class
 * upstream: [SR-010]
 * downstream: [T-015]
 */
class DataService {
    constructor() {
        this.data = [];
    }

    fetch() {
        return this.data;
    }
}


// Example 4: Using 'auto' ID generation

/**
 * @contextgit
 * id: auto
 * type: code
 * title: Helper Function
 * status: draft
 */
function helperFunction() {
    return "helper";
}


// Example 5: Minimal required fields

/**
 * @contextgit
 * id: C-020
 * type: code
 * title: Simple Function
 */
function simpleFunction() {
    return true;
}


// Example 6: TypeScript interface metadata

/**
 * @contextgit
 * id: C-021
 * type: code
 * title: User Type Definition
 * upstream: [SR-011]
 * tags: [types, interfaces]
 */
interface User {
    id: string;
    username: string;
    email: string;
}


// Example 7: Multiple metadata blocks in one file

/**
 * @contextgit
 * id: C-022
 * type: code
 * title: Validation Module
 */
const ValidationModule = {
    /**
     * @contextgit
     * id: C-023
     * type: code
     * title: Email Validator
     * upstream: [C-022]
     */
    validateEmail: function(email) {
        return email.includes('@');
    }
};
