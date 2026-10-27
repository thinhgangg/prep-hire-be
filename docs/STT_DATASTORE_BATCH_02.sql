begin;

-- Batch 02: 100 thuat ngu moi, khong trung Batch 01.
-- Cach doc chi la du lieu goi y va duoc de is_verified = false.

create temporary table _stt_batch_02 (
    canonical_text text,
    normalized_key text,
    category text,
    pronunciation_text text,
    ambiguity_level text,
    auto_correct boolean,
    context_text text
) on commit drop;

insert into _stt_batch_02 values
('Dart', 'dart', 'programming_language', 'đát', 'medium', false, 'Flutter'),
('Ruby', 'ruby', 'programming_language', 'ru bi', 'medium', false, 'Rails'),
('Scala', 'scala', 'programming_language', 'sca la', 'low', true, 'JVM'),
('R', 'rlang', 'programming_language', 'a', 'high', false, 'statistics'),
('MATLAB', 'matlab', 'programming_language', 'mát láp', 'low', true, 'numerical computing'),
('Bash', 'bash', 'programming_language', 'bát', 'high', false, 'shell'),
('PowerShell', 'powershell', 'programming_language', 'pao ờ seo', 'medium', false, 'Windows'),
('Solidity', 'solidity', 'programming_language', 'sờ li đi ti', 'low', true, 'smart contract'),
('Lua', 'lua', 'programming_language', 'lu a', 'medium', false, 'scripting'),
('Perl', 'perl', 'programming_language', 'pơ l', 'medium', false, 'scripting'),
('Svelte', 'svelte', 'frontend_framework', 'sờ ven t', 'low', true, 'frontend'),
('Nuxt.js', 'nuxtjs', 'frontend_framework', 'nấc giây ét', 'medium', false, 'Vue.js'),
('Vite', 'vite', 'frontend_tool', 'vít', 'high', false, 'build tool'),
('Webpack', 'webpack', 'frontend_tool', 'web péc', 'low', true, 'bundle'),
('Babel', 'babel', 'frontend_tool', 'bây bồ', 'medium', false, 'transpiler'),
('Tailwind CSS', 'tailwindcss', 'frontend_framework', 'thây uyn xi ét ét', 'low', true, 'utility CSS'),
('Bootstrap', 'bootstrap', 'frontend_framework', 'bút sờ tráp', 'medium', false, 'CSS'),
('Sass', 'sass', 'frontend_tool', 'sát', 'high', false, 'CSS'),
('Redux Toolkit', 'reduxtoolkit', 'frontend_library', 'ri đắc tun kít', 'low', true, 'state management'),
('jQuery', 'jquery', 'frontend_library', 'giây que ri', 'medium', false, 'DOM'),
('Laravel', 'laravel', 'backend_framework', 'la ra veo', 'low', true, 'PHP'),
('ASP.NET Core', 'aspnetcore', 'backend_framework', 'ây ét pi đót nét co', 'low', true, 'C#'),
('Flask', 'flask', 'backend_framework', 'phờ lát', 'medium', false, 'Python'),
('Ruby on Rails', 'rubyonrails', 'backend_framework', 'ru bi on râyl', 'low', true, 'Ruby'),
('Gin', 'gin', 'backend_framework', 'gin', 'high', false, 'Go'),
('Fiber', 'fiber', 'backend_framework', 'phai bờ', 'high', false, 'Go'),
('Koa.js', 'koajs', 'backend_framework', 'cô a giây ét', 'medium', false, 'Node.js'),
('Spring Framework', 'springframework', 'backend_framework', 'sờ pờ ring phờ rêm quớc', 'low', true, 'Java'),
('Hibernate', 'hibernate', 'backend_library', 'hai bơ nây t', 'medium', false, 'Java ORM'),
('Prisma', 'prisma', 'backend_library', 'pờ ri sờ ma', 'medium', false, 'ORM'),
('MariaDB', 'mariadb', 'database', 'ma ri a đi bi', 'low', true, 'SQL'),
('Oracle Database', 'oracledatabase', 'database', 'o ra cồ đâу ta bây s', 'medium', false, 'SQL'),
('SQL Server', 'sqlserver', 'database', 'ét kiu eo sơ vờ', 'medium', false, 'Microsoft'),
('Cassandra', 'cassandra', 'database', 'ca san đờ ra', 'low', true, 'NoSQL'),
('CouchDB', 'couchdb', 'database', 'cao ch đi bi', 'low', true, 'NoSQL'),
('DynamoDB', 'dynamodb', 'database', 'đai na mô đi bi', 'low', true, 'AWS'),
('Elasticsearch', 'elasticsearch', 'database', 'i lát tích sớt', 'low', true, 'search engine'),
('Neo4j', 'neo4j', 'database', 'ni ô pho giây', 'low', true, 'graph database'),
('Firestore', 'firestore', 'database', 'phai ờ sờ to', 'low', true, 'Firebase'),
('InfluxDB', 'influxdb', 'database', 'in phờ lấc đi bi', 'low', true, 'time series'),
('Terraform', 'terraform', 'devops', 'te ra pho m', 'low', true, 'infrastructure as code'),
('Ansible', 'ansible', 'devops', 'an si bồ', 'low', true, 'automation'),
('Nginx', 'nginx', 'devops', 'en gin ích', 'medium', false, 'web server'),
('Apache Kafka', 'apachekafka', 'devops', 'a pa chi cáp ca', 'low', true, 'message streaming'),
('RabbitMQ', 'rabbitmq', 'devops', 'ra bít em kiu', 'low', true, 'message queue'),
('Prometheus', 'prometheus', 'devops', 'pờ rô mi thi ợt', 'low', true, 'monitoring'),
('Grafana', 'grafana', 'devops', 'gra pha na', 'low', true, 'monitoring'),
('Helm', 'helm', 'devops', 'heo m', 'high', false, 'Kubernetes'),
('Argo CD', 'argocd', 'devops', 'a gô xi đi', 'low', true, 'GitOps'),
('CircleCI', 'circleci', 'devops', 'sơ cồ xi ai', 'low', true, 'CI/CD'),
('Travis CI', 'travisci', 'devops', 'tờ ra vít xi ai', 'low', true, 'CI/CD'),
('Docker Compose', 'dockercompose', 'devops', 'đóc cơ côm pô z', 'low', true, 'container'),
('Amazon EC2', 'amazonec2', 'cloud', 'a ma zon i xi tu', 'low', true, 'AWS'),
('Amazon S3', 'amazons3', 'cloud', 'a ma zon ét ba', 'low', true, 'AWS'),
('AWS Lambda', 'awslambda', 'cloud', 'ây đắp liu ét lam đa', 'low', true, 'serverless'),
('NumPy', 'numpy', 'ai_ml_library', 'năm pai', 'low', true, 'Python'),
('pandas', 'pandas', 'ai_ml_library', 'pan đát', 'medium', false, 'dataframe'),
('PyTorch', 'pytorch', 'ai_ml_library', 'pai to ch', 'low', true, 'deep learning'),
('TensorFlow', 'tensorflow', 'ai_ml_library', 'ten sơ phờ lâu', 'low', true, 'deep learning'),
('scikit-learn', 'scikitlearn', 'ai_ml_library', 'sai kít lơn', 'low', true, 'machine learning'),
('OpenCV', 'opencv', 'ai_ml_library', 'âu pần xi vi', 'low', true, 'computer vision'),
('Hugging Face', 'huggingface', 'ai_platform', 'hắc ging phâу s', 'low', true, 'transformer'),
('LangChain', 'langchain', 'ai_ml_library', 'lang châyn', 'low', true, 'LLM'),
('Llama', 'llama', 'ai_model', 'la ma', 'medium', false, 'Meta AI'),
('Gemini', 'gemini', 'ai_model', 'gie mi nai', 'medium', false, 'Google AI'),
('Claude', 'claude', 'ai_model', 'cờ lao đ', 'medium', false, 'Anthropic'),
('Whisper', 'whisper', 'ai_model', 'uýt pờ', 'medium', false, 'speech to text'),
('Jupyter Notebook', 'jupyternotebook', 'data_tool', 'giu pi tờ nốt búc', 'low', true, 'Python'),
('Apache Spark', 'apachespark', 'data_tool', 'a pa chi sờ pác', 'low', true, 'big data'),
('Apache Airflow', 'apacheairflow', 'data_tool', 'a pa chi e phờ lâu', 'low', true, 'workflow'),
('HTTPS', 'https', 'security', 'hát ti ti pi ét', 'medium', false, 'web security'),
('SSL/TLS', 'ssltls', 'security', 'ét ét eo ti eo ét', 'low', true, 'encryption'),
('CORS', 'cors', 'security', 'co s', 'high', false, 'browser'),
('CSRF', 'csrf', 'security', 'xi ét a ép', 'high', false, 'web attack'),
('XSS', 'xss', 'security', 'ích ét ét', 'high', false, 'web attack'),
('SQL Injection', 'sqlinjection', 'security', 'ét kiu eo in giéc sần', 'low', true, 'database attack'),
('bcrypt', 'bcrypt', 'security', 'bi cờ ríp', 'low', true, 'password hashing'),
('AES', 'aes', 'security', 'ây i ét', 'high', false, 'encryption'),
('Postman', 'postman', 'testing_tool', 'pốt man', 'medium', false, 'API testing'),
('Swagger', 'swagger', 'testing_tool', 'sờ goa gờ', 'low', true, 'API documentation'),
('OpenAPI', 'openapi', 'api', 'âu pần a pi ai', 'low', true, 'API specification'),
('pytest', 'pytest', 'testing_framework', 'pai test', 'low', true, 'Python testing'),
('Jest', 'jest', 'testing_framework', 'giét', 'high', false, 'JavaScript testing'),
('Cypress', 'cypress', 'testing_framework', 'sai pờ rét', 'medium', false, 'end to end testing'),
('Selenium', 'selenium', 'testing_framework', 'si li ni ờ m', 'low', true, 'browser automation'),
('Playwright', 'playwright', 'testing_framework', 'pờ lâу rai t', 'medium', false, 'browser testing'),
('JUnit', 'junit', 'testing_framework', 'giây diu nít', 'low', true, 'Java testing'),
('Maven', 'maven', 'build_tool', 'mâу vần', 'medium', false, 'Java build'),
('Gradle', 'gradle', 'build_tool', 'gờ râу đồ', 'medium', false, 'build automation'),
('npm', 'npm', 'package_manager', 'en pi em', 'high', false, 'Node.js'),
('Yarn', 'yarn', 'package_manager', 'dan', 'high', false, 'JavaScript package'),
('pnpm', 'pnpm', 'package_manager', 'pi en pi em', 'low', true, 'JavaScript package'),
('Microservices', 'microservices', 'architecture', 'mai cờ rô sơ vít', 'low', true, 'distributed system'),
('MVC', 'mvc', 'architecture', 'em vi xi', 'high', false, 'software pattern'),
('ORM', 'orm', 'architecture', 'ô a em', 'high', false, 'database mapping'),
('CI/CD', 'cicd', 'devops', 'xi ai xi đi', 'low', true, 'automation pipeline'),
('Agile', 'agile', 'methodology', 'a giai', 'medium', false, 'software development'),
('Scrum', 'scrum', 'methodology', 'sờ cờ răm', 'medium', false, 'Agile'),
('gRPC', 'grpc', 'api', 'gi a pi xi', 'low', true, 'remote procedure call'),
('SOAP', 'soap', 'api', 'sâu p', 'high', false, 'web service');

insert into public.stt_terms
    (canonical_text, normalized_key, category, ambiguity_level, auto_correct, description)
select
    canonical_text,
    normalized_key,
    category,
    ambiguity_level,
    auto_correct,
    'Imported from STT datastore batch 02'
from _stt_batch_02
on conflict (normalized_key) do update set
    canonical_text = excluded.canonical_text,
    category = excluded.category,
    ambiguity_level = excluded.ambiguity_level,
    auto_correct = excluded.auto_correct,
    updated_at = now();

insert into public.stt_term_pronunciations
    (term_id, pronunciation_text, normalized_text, pronunciation_type, locale, source, is_verified)
select
    t.id,
    b.pronunciation_text,
    lower(trim(b.pronunciation_text)),
    'preferred',
    'vi-VN',
    'manual_seed_batch_02',
    false
from _stt_batch_02 b
join public.stt_terms t using (normalized_key)
on conflict (term_id, normalized_text) do nothing;

insert into public.stt_term_contexts
    (term_id, context_text, normalized_text, weight, is_required)
select
    t.id,
    b.context_text,
    lower(trim(b.context_text)),
    1.5,
    false
from _stt_batch_02 b
join public.stt_terms t using (normalized_key)
on conflict (term_id, normalized_text) do update set
    context_text = excluded.context_text,
    weight = excluded.weight;

commit;

select
    (select count(*) from public.stt_terms) as total_terms,
    (select count(*) from public.stt_term_pronunciations) as total_pronunciations,
    (select count(*) from public.stt_term_contexts) as total_contexts,
    (select count(*) from public.stt_term_pronunciations where source = 'manual_seed_batch_02')
        as batch_02_pronunciations;
