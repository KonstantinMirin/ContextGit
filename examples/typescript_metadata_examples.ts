/**
 * Examples of contextgit metadata in TypeScript files.
 *
 * TypeScript uses the same JSDoc format as JavaScript.
 */

// Example 1: TypeScript function with type annotations

/**
 * @contextgit
 * id: C-024
 * type: code
 * title: Typed Authentication Function
 * upstream: [SR-012]
 * tags: [typescript, auth]
 */
function authenticateTyped(username: string, password: string): Promise<boolean> {
    return Promise.resolve(true);
}


// Example 2: Generic function with metadata

/**
 * @contextgit
 * id: C-025
 * type: code
 * title: Generic Data Fetcher
 * upstream: [SR-013]
 */
async function fetchData<T>(url: string): Promise<T> {
    const response = await fetch(url);
    return response.json();
}


// Example 3: Interface definition

/**
 * @contextgit
 * id: C-026
 * type: code
 * title: Application Configuration Interface
 * upstream: [SR-014]
 * tags: [types, config]
 */
interface AppConfig {
    apiUrl: string;
    timeout: number;
    retries: number;
}


// Example 4: Type alias

/**
 * @contextgit
 * id: C-027
 * type: code
 * title: User Role Type
 * upstream: [SR-015]
 */
type UserRole = 'admin' | 'user' | 'guest';


// Example 5: React TypeScript component

/**
 * @contextgit
 * id: C-028
 * type: code
 * title: Typed Button Component
 * upstream: [SR-016]
 * tags: [react, typescript, ui]
 */
interface ButtonProps {
    onClick: () => void;
    label: string;
    disabled?: boolean;
}

function Button({ onClick, label, disabled = false }: ButtonProps) {
    return <button onClick={onClick} disabled={disabled}>{label}</button>;
}


// Example 6: Class with decorators

/**
 * @contextgit
 * id: C-029
 * type: code
 * title: User Service Class
 * upstream: [SR-017]
 */
class UserService {
    private users: User[] = [];

    async getUser(id: string): Promise<User | null> {
        return this.users.find(u => u.id === id) || null;
    }

    async createUser(user: User): Promise<void> {
        this.users.push(user);
    }
}


// Example 7: Enum definition

/**
 * @contextgit
 * id: C-030
 * type: code
 * title: HTTP Status Code Enum
 * tags: [enums, http]
 */
enum HttpStatus {
    OK = 200,
    Created = 201,
    BadRequest = 400,
    Unauthorized = 401,
    NotFound = 404,
    InternalError = 500
}
