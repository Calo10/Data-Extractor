from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer

def main():
    # Create authorizer
    authorizer = DummyAuthorizer()
    
    # Add anonymous user with write permissions
    # The path should be the directory where you want to allow uploads
    authorizer.add_anonymous("/path/to/your/ftp/directory", perm="elradfmwM")
    # Permissions explained:
    # e - change directory
    # l - list files
    # r - retrieve file
    # a - append data
    # d - delete file
    # f - rename file
    # m - create directory
    # w - store file
    # M - can create directories

    # Create handler
    handler = FTPHandler
    handler.authorizer = authorizer
    
    # Configure handler
    handler.banner = "Welcome to FTP server"
    handler.passive_ports = range(60000, 65535)
    
    # Create and start server
    address = ("192.168.0.118", 2121)
    server = FTPServer(address, handler)
    
    # Set limits
    server.max_cons = 256
    server.max_cons_per_ip = 5
    
    # Start server
    server.serve_forever()

if __name__ == "__main__":
    main() 