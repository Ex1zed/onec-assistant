CREATE TABLE modules (
  id INT AUTO_INCREMENT PRIMARY KEY,
  path VARCHAR(500) NOT NULL UNIQUE,
  object_name VARCHAR(300),
  module_type VARCHAR(100)
);

CREATE TABLE procedures (
  id INT AUTO_INCREMENT PRIMARY KEY,
  module_id INT NOT NULL,
  name VARCHAR(255) NOT NULL,
  kind VARCHAR(20) NOT NULL,
  params TEXT,
  exported BOOLEAN NOT NULL DEFAULT FALSE,
  body MEDIUMTEXT NOT NULL,
  body_hash CHAR(64) NOT NULL,
  indexed_hash CHAR(64),
  UNIQUE KEY uq_module_proc (module_id, name),
  KEY idx_name (name),
  FOREIGN KEY (module_id) REFERENCES modules(id) ON DELETE CASCADE
);

CREATE TABLE calls (
  caller_id INT NOT NULL,
  callee_id INT NOT NULL,
  PRIMARY KEY (caller_id, callee_id),
  FOREIGN KEY (caller_id) REFERENCES procedures(id) ON DELETE CASCADE,
  FOREIGN KEY (callee_id) REFERENCES procedures(id) ON DELETE CASCADE
);

CREATE TABLE docs (
  id INT AUTO_INCREMENT PRIMARY KEY,
  procedure_id INT NOT NULL,
  content_md MEDIUMTEXT NOT NULL,
  source_hash CHAR(64) NOT NULL,
  version INT NOT NULL DEFAULT 1,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  KEY idx_proc (procedure_id),
  FOREIGN KEY (procedure_id) REFERENCES procedures(id) ON DELETE CASCADE
);

CREATE TABLE feedback (
  id INT AUTO_INCREMENT PRIMARY KEY,
  question TEXT NOT NULL,
  answer MEDIUMTEXT NOT NULL,
  procedure_ids JSON,
  verdict VARCHAR(10) NOT NULL,
  comment TEXT,
  resolved BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
