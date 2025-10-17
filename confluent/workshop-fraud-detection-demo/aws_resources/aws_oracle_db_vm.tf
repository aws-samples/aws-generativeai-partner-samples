
# Generate random passwords for Oracle DB
# Oracle password requirements: 8-30 chars, at least 1 uppercase, 1 lowercase, 1 digit
# No special characters to avoid quoting issues in SQL statements
resource "random_password" "oracle_db_password" {
  length  = 10
  special = false
  min_upper = 2
  min_lower = 2
  min_numeric = 2
}

resource "random_password" "oracle_xstream_user_password" {
  length  = 10
  special = false
  min_upper = 2
  min_lower = 2
  min_numeric = 2
}

# Optional: Define a variable for mapping AMIs to the correct SSH user
variable "ssh_user" {
  description = "SSH user based on AMI type"
  type        = map(string)
  default     = {
    # Amazon Linux
    "ami-0c55b159cbfafe1f0" = "ec2-user"
    # Ubuntu
    "ami-0885b1f6bd170450c" = "ubuntu"
    # RHEL
    "ami-0b0af3577fe5e3532" = "ec2-user"
    # Debian
    "ami-0bd9223868b4778d7" = "admin"
    # CentOS
    "ami-0f2b4fc905b0bd1f1" = "centos"
    # Oracle Linux
    "ami-07af4f1c7eb1971ff" = "ec2-user"
  }
}
# IAM role for EC2 instance
resource "aws_iam_role" "oracle_instance_role" {
  name = "${var.prefix}-oracle-instance-role-${random_id.env_display_id.hex}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${var.prefix}-oracle-instance-role-${random_id.env_display_id.hex}"
  }
}

resource "aws_iam_role_policy_attachment" "oracle_ssm" {
  role       = aws_iam_role.oracle_instance_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "oracle_instance_profile" {
  name = "${var.prefix}-oracle-instance-profile-${random_id.env_display_id.hex}"
  role = aws_iam_role.oracle_instance_role.name
}

# Security group for EC2 instance
resource "aws_security_group" "allow_ssh_oracle" {
  name        = "${var.prefix}_allow_ssh_oracle"
  description = "Allow SSH and Oracle inbound traffic"
  vpc_id      = aws_vpc.main.id
  ingress {
    description = "SSH access from VPC only"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }
  ingress {
    description = "Oracle SQL*Net access from VPC"
    from_port   = 1521
    to_port     = 1521
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }
  ingress {
    description = "Oracle SQL*Net access from NAT Gateway (for EKS pods)"
    from_port   = 1521
    to_port     = 1521
    protocol    = "tcp"
    cidr_blocks = ["${aws_eip.eip.public_ip}/32"]
  }
  ingress {
    description = "Oracle SQL*Net access from allowed external IPs"
    from_port   = 1521
    to_port     = 1521
    protocol    = "tcp"
    cidr_blocks = [
      "3.217.171.197/32",
      "3.227.73.0/32",
      "3.234.42.230/32",
      "18.204.235.237/32",
      "18.232.30.126/32",
      "34.204.253.120/32",
      "34.205.233.46/32",
      "34.231.151.179/32",
      "35.173.154.142/32",
      "52.3.108.122/32",
      "52.4.168.0/32",
      "52.5.120.21/32",
      "52.45.226.34/32",
      "52.55.155.248/32",
      "52.73.34.234/32",
      "52.201.77.94/32",
      "54.83.252.163/32",
      "54.146.88.203/32",
      "54.156.105.40/32",
      "54.172.40.193/32",
      "54.204.102.217/32",
      "54.204.113.211/32",
      "54.237.164.14/32",
      "54.242.207.111/32",
      "54.243.244.175/32",
      "100.24.204.241/32",
      "107.21.116.39/32"
    ]
  }
  ingress {
    description = "Oracle EM Express access from VPC"
    from_port   = 5500
    to_port     = 5500
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }
  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = {
    Name = "${var.prefix}-oracle-sg"
  }
}


data "aws_ami" "oracle_ami" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-2023*"]
  }

  filter {
    name   = "architecture"
    values = ["x86_64"]
  }
}

# EC2 instance for Oracle
# /var/log/cloud-init.log
#/var/log/cloud-init-output.log
# /var/lib/cloud/instances/i-0c42e1665ff8e11f2/user-data.txt
# sudo cat /var/lib/cloud/instance/scripts/part-001
resource "aws_instance" "oracle_instance" {
  ami = data.aws_ami.oracle_ami.id
  instance_type = "t3.large"
  key_name      = aws_key_pair.tf_key.key_name
  subnet_id              = aws_subnet.public_subnets[0].id # Associate with the first public subnet - put this in private subnet?
  iam_instance_profile   = aws_iam_instance_profile.oracle_instance_profile.name
  monitoring             = true  # Enable detailed monitoring
  ebs_optimized          = true  # Enable EBS optimization

  vpc_security_group_ids = [aws_security_group.allow_ssh_oracle.id]
  
  # Enforce IMDSv2
  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"  # Require IMDSv2
    http_put_response_hop_limit = 1
    instance_metadata_tags      = "enabled"
  }

  root_block_device {
    volume_size = 30  # Oracle XE needs at least 12GB, adding extra space
    volume_type = "gp3"
    encrypted   = true  # Enable EBS encryption
  }

  user_data_replace_on_change = true
  user_data = <<-EOF
    #!/bin/bash
    # Update system
    dnf update -y
    
    # Install Docker
    dnf install -y docker
    systemctl enable docker
    systemctl start docker
    
    # Install Docker Compose
    curl -L "https://github.com/docker/compose/releases/download/v2.20.3/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    
    # Create directory for Oracle data
    mkdir -p /opt/oracle/oradata
    chmod -R 777 /opt/oracle/oradata
    
    # Create docker-compose.yml file
    cat > /opt/oracle/docker-compose.yml <<DOCKER_COMPOSE
    version: '3'
    services:
      oracle-xe:
        image: container-registry.oracle.com/database/express:21.3.0-xe
        container_name: oracle-xe
        ports:
          - "1521:1521"
          - "5500:5500"
        environment:
          - ORACLE_PWD=${random_password.oracle_db_password.result}
          - ORACLE_CHARACTERSET=AL32UTF8
        volumes:
          - /opt/oracle/oradata:/opt/oracle/oradata
        restart: always
    DOCKER_COMPOSE
    
    # Pull Oracle XE image and start container
    cd /opt/oracle
    docker-compose up -d
    
    # Set up a welcome message
    echo "Oracle XE 21c setup complete. Connect using:"
    echo "Hostname: $(curl -s http://169.254.169.254/latest/meta-data/public-hostname)"
    echo "Port: 1521"
    echo "SID: XE"
    echo "PDB: XEPDB1"
    echo "Username: system"
    echo "Password: ${random_password.oracle_db_password.result}"
    echo "EM Express URL: https://$(curl -s http://169.254.169.254/latest/meta-data/public-hostname):5500/em"

    echo "Waiting for oracle-xe container to become healthy"
    until [ "$(sudo docker inspect -f '{{.State.Health.Status}}' oracle-xe 2>/dev/null)" == "healthy" ]; do
      echo -n "."
      sleep 10
    done

    echo "Writing XStream setup script"
    cat > /opt/oracle/setup-xstream.sh <<SCRIPT_EOF
    #!/bin/bash
    set -e
    log() { echo "[XSTREAM] \$1"; }

    log "Enable Oracle XStream"
    sudo docker exec -i oracle-xe bash -c "ORACLE_SID=XE; export ORACLE_SID; sqlplus /nolog" <<SQL_EOF
    CONNECT sys/${random_password.oracle_db_password.result} AS SYSDBA
    ALTER SYSTEM SET enable_goldengate_replication=TRUE SCOPE=BOTH;
    SHOW PARAMETER GOLDEN;
    EXIT;
    SQL_EOF

    log "Configure ARCHIVELOG mode"
    sudo docker exec -i oracle-xe bash -c "ORACLE_SID=XE; export ORACLE_SID; sqlplus /nolog" <<SQL_EOF
    CONNECT sys/${random_password.oracle_db_password.result} AS SYSDBA
    SHUTDOWN IMMEDIATE;
    STARTUP MOUNT;
    ALTER DATABASE ARCHIVELOG;
    ALTER DATABASE OPEN;
    EXIT;
    SQL_EOF

    log "Configure supplemental logging"
    sudo docker exec -i oracle-xe bash -c "ORACLE_SID=XE; export ORACLE_SID; sqlplus /nolog" <<SQL_EOF
    CONNECT sys/${random_password.oracle_db_password.result} AS SYSDBA
    ALTER SESSION SET CONTAINER = CDB\$ROOT;
    ALTER DATABASE ADD SUPPLEMENTAL LOG DATA (ALL) COLUMNS;
    SELECT SUPPLEMENTAL_LOG_DATA_MIN, SUPPLEMENTAL_LOG_DATA_ALL FROM V\\$DATABASE;
    EXIT;
    SQL_EOF

    log "Create XStream tablespaces in CDB"
    sudo docker exec -i oracle-xe bash -c "ORACLE_SID=XE; export ORACLE_SID; sqlplus /nolog" <<SQL_EOF
    CONNECT sys/${random_password.oracle_db_password.result} AS SYSDBA
    CREATE TABLESPACE xstream_adm_tbs DATAFILE '/opt/oracle/oradata/XE/xstream_adm_tbs.dbf'
    SIZE 25M REUSE AUTOEXTEND ON MAXSIZE UNLIMITED;

    CREATE TABLESPACE xstream_tbs DATAFILE '/opt/oracle/oradata/XE/xstream_tbs.dbf'
    SIZE 25M REUSE AUTOEXTEND ON MAXSIZE UNLIMITED;
    EXIT;
    SQL_EOF

    log "Create PDB objects and sample user"
    sudo docker exec -i oracle-xe bash -c "ORACLE_SID=XE; export ORACLE_SID; sqlplus /nolog" <<SQL_EOF
    CONNECT sys/${random_password.oracle_db_password.result} AS SYSDBA
    ALTER SESSION SET CONTAINER=XEPDB1;

    CREATE USER sample IDENTIFIED BY "${random_password.oracle_db_password.result}";
    GRANT CONNECT, RESOURCE TO sample;
    ALTER USER sample QUOTA UNLIMITED ON USERS;

    CREATE TABLESPACE xstream_adm_tbs DATAFILE '/opt/oracle/oradata/XE/XEPDB1/xstream_adm_tbs.dbf'
    SIZE 25M REUSE AUTOEXTEND ON MAXSIZE UNLIMITED;

    CREATE TABLESPACE xstream_tbs DATAFILE '/opt/oracle/oradata/XE/XEPDB1/xstream_tbs.dbf'
    SIZE 25M REUSE AUTOEXTEND ON MAXSIZE UNLIMITED;
    EXIT;
    SQL_EOF

    log "Create XStream admin user"
    sudo docker exec -i oracle-xe bash -c "ORACLE_SID=XE; export ORACLE_SID; sqlplus /nolog" <<SQL_EOF
    CONNECT sys/${random_password.oracle_db_password.result} AS SYSDBA
    CREATE USER c##cfltadmin IDENTIFIED BY "${random_password.oracle_xstream_user_password.result}"
    DEFAULT TABLESPACE xstream_adm_tbs
    QUOTA UNLIMITED ON xstream_adm_tbs
    CONTAINER=ALL;

    GRANT CREATE SESSION TO c##cfltadmin CONTAINER=ALL;
    GRANT SET CONTAINER TO c##cfltadmin CONTAINER=ALL;

    BEGIN
      DBMS_XSTREAM_AUTH.GRANT_ADMIN_PRIVILEGE(
        grantee                 => 'c##cfltadmin',
        privilege_type          => 'CAPTURE',
        grant_select_privileges => TRUE,
        container               => 'ALL'
      );
    END;
    /
    EXIT;
    SQL_EOF

    log "Create XStream connect user"
    sudo docker exec -i oracle-xe bash -c "ORACLE_SID=XE; export ORACLE_SID; sqlplus /nolog" <<SQL_EOF
    CONNECT sys/${random_password.oracle_db_password.result} AS SYSDBA
    CREATE USER c##cfltuser IDENTIFIED BY "${random_password.oracle_xstream_user_password.result}"
    DEFAULT TABLESPACE xstream_tbs
    QUOTA UNLIMITED ON xstream_tbs
    CONTAINER=ALL;

    GRANT CREATE SESSION TO c##cfltuser CONTAINER=ALL;
    GRANT SET CONTAINER TO c##cfltuser CONTAINER=ALL;
    GRANT SELECT_CATALOG_ROLE TO c##cfltuser CONTAINER=ALL;
    GRANT CREATE TABLE, CREATE SEQUENCE, CREATE TRIGGER TO c##cfltuser CONTAINER=ALL;
    GRANT FLASHBACK ANY TABLE, SELECT ANY TABLE, LOCK ANY TABLE TO c##cfltuser CONTAINER=ALL;
    EXIT;
    SQL_EOF

    log "Create XStream Outbound Server"
    sudo docker exec -i oracle-xe sqlplus c\#\#cfltadmin/${random_password.oracle_xstream_user_password.result}@//localhost:1521/XE <<SQL_EOF
    DECLARE
      tables  DBMS_UTILITY.UNCL_ARRAY;
      schemas DBMS_UTILITY.UNCL_ARRAY;
    BEGIN
      tables(1) := NULL;
      schemas(1) := 'sample';
      DBMS_XSTREAM_ADM.CREATE_OUTBOUND(
        server_name => 'xout',
        source_container_name => 'XEPDB1',
        table_names => tables,
        schema_names => schemas);
    END;
    /
    EXIT;
    SQL_EOF

    sudo docker exec -i oracle-xe bash -c "ORACLE_SID=XE; export ORACLE_SID; sqlplus /nolog" <<SQL_EOF
    CONNECT sys/${random_password.oracle_db_password.result} AS SYSDBA
    BEGIN
      DBMS_XSTREAM_ADM.ALTER_OUTBOUND(
        server_name  => 'xout',
        connect_user => 'c##cfltuser');
    END;
    /
    EXIT;
    SQL_EOF

    log "XStream configuration complete"

    SCRIPT_EOF

    chmod +x /opt/oracle/setup-xstream.sh
    bash /opt/oracle/setup-xstream.sh >> /var/log/xstream-setup.log 2>&1

    echo "Oracle XE with XStream configured." | tee -a /var/log/user-data.log

  EOF
  tags = {
    Name        = "${var.prefix}-oracle-xe"
  }
}

output "oracle_vm_db_details" {
  value = {
    "private_ip": aws_instance.oracle_instance.private_ip
    "connection_string": "sqlplus system/${nonsensitive(random_password.oracle_db_password.result)}@${aws_instance.oracle_instance.private_ip}:1521/XEPDB1"
    "express_url": "https://${aws_instance.oracle_instance.private_ip}:5500/em"
  }
}


output "oracle_xstream_connector" {
  value = {
    database_hostname = aws_instance.oracle_instance.public_dns
    database_port = var.oracle_db_port
    database_username = var.oracle_xstream_user_username
    database_password = nonsensitive(random_password.oracle_xstream_user_password.result)
    database_name = var.oracle_db_name
    database_service_name = var.oracle_db_name
    pluggable_database_name = var.oracle_pdb_name
    xstream_outbound_server = var.oracle_xtream_outbound_server_name
    table_inclusion_regex = "SAMPLE[.](USER_TRANSACTION|AUTH_USER)"
    topic_prefix = "fd"
    decimal_handling_mode = "double"
  }
}