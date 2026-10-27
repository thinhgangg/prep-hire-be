begin;

-- Batch 01: 50 thuat ngu IT pho bien.
-- Idempotent: co the chay lai ma khong tao ban ghi trung.

insert into public.stt_terms
    (canonical_text, normalized_key, category, ambiguity_level, auto_correct, description)
values
    ('ChatGPT',       'chatgpt',       'ai_tool',              'low',    true,  'Tro ly AI hoi thoai cua OpenAI'),
    ('JavaScript',    'javascript',    'programming_language', 'medium', false, 'Ngon ngu lap trinh pho bien tren web'),
    ('TypeScript',    'typescript',    'programming_language', 'low',    true,  'Ngon ngu mo rong JavaScript voi kieu tinh'),
    ('Python',        'python',        'programming_language', 'medium', false, 'Ngon ngu lap trinh da muc dich'),
    ('Java',          'java',          'programming_language', 'high',   false, 'Ngon ngu lap trinh Java'),
    ('C++',           'cplusplus',     'programming_language', 'high',   false, 'Ngon ngu lap trinh C++'),
    ('C#',            'csharp',        'programming_language', 'high',   false, 'Ngon ngu lap trinh C#'),
    ('Go',            'go',            'programming_language', 'high',   false, 'Ngon ngu lap trinh Go'),
    ('PHP',           'php',           'programming_language', 'medium', false, 'Ngon ngu lap trinh PHP'),
    ('Kotlin',        'kotlin',        'programming_language', 'low',    true,  'Ngon ngu lap trinh Kotlin'),
    ('Swift',         'swift',         'programming_language', 'high',   false, 'Ngon ngu lap trinh Swift'),
    ('Rust',          'rust',          'programming_language', 'high',   false, 'Ngon ngu lap trinh Rust'),
    ('ReactJS',       'reactjs',       'frontend_framework',   'medium', false, 'Thu vien giao dien ReactJS'),
    ('Angular',       'angular',       'frontend_framework',   'low',    true,  'Framework frontend Angular'),
    ('Vue.js',        'vuejs',         'frontend_framework',   'medium', false, 'Framework frontend Vue.js'),
    ('Next.js',       'nextjs',        'frontend_framework',   'medium', false, 'Framework React Next.js'),
    ('Node.js',       'nodejs',        'backend_runtime',      'medium', false, 'Moi truong chay JavaScript Node.js'),
    ('Express.js',    'expressjs',     'backend_framework',    'medium', false, 'Framework backend Express.js'),
    ('NestJS',        'nestjs',        'backend_framework',    'medium', false, 'Framework backend NestJS'),
    ('FastAPI',       'fastapi',       'backend_framework',    'low',    true,  'Framework API Python FastAPI'),
    ('Django',        'django',        'backend_framework',    'low',    true,  'Framework web Python Django'),
    ('Spring Boot',   'springboot',    'backend_framework',    'low',    true,  'Framework backend Java Spring Boot'),
    ('REST API',      'restapi',       'api',                  'medium', false, 'API theo phong cach REST'),
    ('GraphQL',       'graphql',       'api',                  'low',    true,  'Ngon ngu truy van API GraphQL'),
    ('WebSocket',     'websocket',     'api',                  'low',    true,  'Giao thuc ket noi hai chieu WebSocket'),
    ('PostgreSQL',    'postgresql',    'database',             'low',    true,  'He quan tri co so du lieu PostgreSQL'),
    ('MySQL',         'mysql',         'database',             'low',    true,  'He quan tri co so du lieu MySQL'),
    ('MongoDB',       'mongodb',       'database',             'low',    true,  'Co so du lieu tai lieu MongoDB'),
    ('Redis',         'redis',         'database',             'medium', false, 'Kho du lieu trong bo nho Redis'),
    ('SQLite',        'sqlite',        'database',             'low',    true,  'Co so du lieu nhung SQLite'),
    ('Supabase',      'supabase',      'database_platform',    'low',    true,  'Nen tang backend Supabase'),
    ('Firebase',      'firebase',      'database_platform',    'low',    true,  'Nen tang backend Firebase'),
    ('Docker',        'docker',        'devops',               'low',    true,  'Nen tang container Docker'),
    ('Kubernetes',    'kubernetes',    'devops',               'low',    true,  'Nen tang dieu phoi container Kubernetes'),
    ('Jenkins',       'jenkins',       'devops',               'low',    true,  'Cong cu CI/CD Jenkins'),
    ('GitHub Actions','githubactions', 'devops',               'low',    true,  'Dich vu CI/CD GitHub Actions'),
    ('AWS',           'aws',           'cloud',                'medium', false, 'Nen tang dam may Amazon Web Services'),
    ('Microsoft Azure','microsoftazure','cloud',               'medium', false, 'Nen tang dam may Microsoft Azure'),
    ('Google Cloud',  'googlecloud',   'cloud',                'medium', false, 'Nen tang dam may Google Cloud'),
    ('Git',           'git',           'development_tool',     'high',   false, 'He thong quan ly phien ban Git'),
    ('GitHub',        'github',        'development_tool',     'medium', false, 'Nen tang luu tru ma nguon GitHub'),
    ('GitLab',        'gitlab',        'development_tool',     'low',    true,  'Nen tang DevOps GitLab'),
    ('Visual Studio Code','visualstudiocode','development_tool','low',   true,  'Trinh soan thao Visual Studio Code'),
    ('Linux',         'linux',         'operating_system',     'medium', false, 'He dieu hanh Linux'),
    ('JWT',           'jwt',           'security',             'high',   false, 'JSON Web Token'),
    ('OAuth',         'oauth',         'security',             'medium', false, 'Chuan uy quyen OAuth'),
    ('JSON',          'json',          'data_format',          'medium', false, 'Dinh dang du lieu JSON'),
    ('HTML',          'html',          'web_standard',         'medium', false, 'Ngon ngu danh dau HTML'),
    ('CSS',           'css',           'web_standard',         'medium', false, 'Ngon ngu dinh kieu CSS'),
    ('SQL',           'sql',           'database_language',    'high',   false, 'Ngon ngu truy van SQL')
on conflict (normalized_key) do update set
    canonical_text = excluded.canonical_text,
    category = excluded.category,
    ambiguity_level = excluded.ambiguity_level,
    auto_correct = excluded.auto_correct,
    description = excluded.description,
    updated_at = now();

-- Cach doc. Moi dong gom: normalized_key, cach doc, loai.
with pronunciation_data(normalized_key, pronunciation_text, pronunciation_type) as (
    values
    ('chatgpt', 'chat gi pi ti', 'preferred'),
    ('chatgpt', 'chat gờ pê tê', 'accepted'),
    ('javascript', 'gia va sờ cờ ríp', 'preferred'),
    ('javascript', 'ja va script', 'accepted'),
    ('typescript', 'thai sờ cờ ríp', 'preferred'),
    ('typescript', 'type script', 'accepted'),
    ('python', 'pai thon', 'preferred'),
    ('python', 'pi thon', 'accepted'),
    ('java', 'gia va', 'preferred'),
    ('cplusplus', 'xi cộng cộng', 'preferred'),
    ('cplusplus', 'c cộng cộng', 'accepted'),
    ('csharp', 'xi sáp', 'preferred'),
    ('csharp', 'c sharp', 'accepted'),
    ('go', 'gâu', 'preferred'),
    ('php', 'pi hát pi', 'preferred'),
    ('kotlin', 'cót lin', 'preferred'),
    ('swift', 'suýp', 'preferred'),
    ('rust', 'rớt', 'preferred'),
    ('reactjs', 'ri ác giây ét', 'preferred'),
    ('reactjs', 'ri ác', 'accepted'),
    ('angular', 'ang gu lờ', 'preferred'),
    ('vuejs', 'viu giây ét', 'preferred'),
    ('vuejs', 'viu', 'accepted'),
    ('nextjs', 'néch giây ét', 'preferred'),
    ('nextjs', 'next giây ét', 'accepted'),
    ('nodejs', 'nốt giây ét', 'preferred'),
    ('nodejs', 'nốt chấm giây ét', 'accepted'),
    ('expressjs', 'ích sờ pờ rét giây ét', 'preferred'),
    ('nestjs', 'nést giây ét', 'preferred'),
    ('fastapi', 'phát a pi ai', 'preferred'),
    ('fastapi', 'fast a pi ai', 'accepted'),
    ('django', 'jang gô', 'preferred'),
    ('springboot', 'sờ pờ ring bút', 'preferred'),
    ('restapi', 'rést a pi ai', 'preferred'),
    ('graphql', 'gráp kiu eo', 'preferred'),
    ('websocket', 'web só két', 'preferred'),
    ('postgresql', 'pốt gờ rét ét kiu eo', 'preferred'),
    ('postgresql', 'pốt gờ rét', 'accepted'),
    ('mysql', 'mai ét kiu eo', 'preferred'),
    ('mongodb', 'mon gô đi bi', 'preferred'),
    ('redis', 're đít', 'preferred'),
    ('sqlite', 'ét kiu eo lai', 'preferred'),
    ('supabase', 'su pờ bây s', 'preferred'),
    ('firebase', 'phai ờ bây s', 'preferred'),
    ('docker', 'đóc cơ', 'preferred'),
    ('kubernetes', 'cu bơ nét tịt', 'preferred'),
    ('kubernetes', 'cu bơ nét', 'accepted'),
    ('jenkins', 'jen kin', 'preferred'),
    ('githubactions', 'gít hắp ác sần', 'preferred'),
    ('aws', 'ây đắp bờ diu ét', 'preferred'),
    ('aws', 'a đắp bờ diu ét', 'accepted'),
    ('microsoftazure', 'mai cờ rô sóp a giơ', 'preferred'),
    ('googlecloud', 'gu gồ cờ lao', 'preferred'),
    ('git', 'gít', 'preferred'),
    ('github', 'gít hắp', 'preferred'),
    ('gitlab', 'gít láp', 'preferred'),
    ('visualstudiocode', 'vi giồ stu đi ô cốt', 'preferred'),
    ('visualstudiocode', 'vi ét cốt', 'accepted'),
    ('linux', 'li núc', 'preferred'),
    ('jwt', 'giây đắp bờ diu ti', 'preferred'),
    ('oauth', 'âu óp', 'preferred'),
    ('json', 'giây son', 'preferred'),
    ('html', 'hát ti em eo', 'preferred'),
    ('css', 'xi ét ét', 'preferred'),
    ('sql', 'ét kiu eo', 'preferred'),
    ('sql', 'si cồ', 'accepted')
)
insert into public.stt_term_pronunciations
    (term_id, pronunciation_text, normalized_text, pronunciation_type, source, is_verified)
select
    t.id,
    p.pronunciation_text,
    lower(trim(p.pronunciation_text)),
    p.pronunciation_type,
    'manual_seed',
    false
from pronunciation_data p
join public.stt_terms t using (normalized_key)
on conflict (term_id, normalized_text) do nothing;

-- Context dung de giam overcorrection.
with context_data(normalized_key, context_text, weight) as (
    values
    ('chatgpt', 'OpenAI', 2.0), ('chatgpt', 'LLM', 1.5), ('chatgpt', 'prompt', 1.0),
    ('javascript', 'frontend', 2.0), ('javascript', 'web', 1.5), ('javascript', 'Node.js', 1.5),
    ('typescript', 'JavaScript', 2.0), ('typescript', 'type', 1.0),
    ('python', 'Django', 1.5), ('python', 'FastAPI', 1.5), ('python', 'machine learning', 1.5),
    ('java', 'Spring Boot', 2.0), ('java', 'JVM', 2.0),
    ('cplusplus', 'compiler', 1.5), ('cplusplus', 'pointer', 1.5),
    ('csharp', '.NET', 2.0), ('csharp', 'ASP.NET', 2.0),
    ('go', 'Golang', 2.0), ('go', 'goroutine', 2.0),
    ('php', 'Laravel', 2.0), ('php', 'backend', 1.0),
    ('kotlin', 'Android', 2.0), ('swift', 'iOS', 2.0), ('rust', 'memory safety', 2.0),
    ('reactjs', 'frontend', 2.0), ('reactjs', 'component', 1.5), ('reactjs', 'hook', 1.5),
    ('angular', 'frontend', 2.0), ('angular', 'component', 1.5),
    ('vuejs', 'frontend', 2.0), ('vuejs', 'component', 1.5),
    ('nextjs', 'ReactJS', 2.0), ('nextjs', 'server-side rendering', 2.0),
    ('nodejs', 'backend', 2.0), ('nodejs', 'npm', 1.5),
    ('expressjs', 'Node.js', 2.0), ('expressjs', 'middleware', 1.5),
    ('nestjs', 'Node.js', 2.0), ('nestjs', 'dependency injection', 1.5),
    ('fastapi', 'Python', 2.0), ('fastapi', 'API', 1.5),
    ('django', 'Python', 2.0), ('django', 'ORM', 1.5),
    ('springboot', 'Java', 2.0), ('springboot', 'microservice', 1.5),
    ('restapi', 'HTTP', 2.0), ('restapi', 'endpoint', 1.5),
    ('graphql', 'query', 1.5), ('graphql', 'schema', 1.5),
    ('websocket', 'realtime', 2.0), ('websocket', 'socket', 1.5),
    ('postgresql', 'database', 2.0), ('postgresql', 'SQL', 1.5),
    ('mysql', 'database', 2.0), ('mysql', 'SQL', 1.5),
    ('mongodb', 'NoSQL', 2.0), ('mongodb', 'document', 1.5),
    ('redis', 'cache', 2.0), ('redis', 'in-memory', 1.5),
    ('sqlite', 'database', 2.0), ('sqlite', 'embedded', 1.5),
    ('supabase', 'PostgreSQL', 2.0), ('supabase', 'authentication', 1.5),
    ('firebase', 'Google', 1.5), ('firebase', 'Firestore', 2.0),
    ('docker', 'container', 2.0), ('docker', 'image', 1.5),
    ('kubernetes', 'container', 2.0), ('kubernetes', 'cluster', 2.0), ('kubernetes', 'pod', 2.0),
    ('jenkins', 'CI/CD', 2.0), ('jenkins', 'pipeline', 1.5),
    ('githubactions', 'CI/CD', 2.0), ('githubactions', 'workflow', 1.5),
    ('aws', 'cloud', 2.0), ('aws', 'EC2', 1.5), ('aws', 'S3', 1.5),
    ('microsoftazure', 'cloud', 2.0), ('microsoftazure', 'Microsoft', 1.5),
    ('googlecloud', 'cloud', 2.0), ('googlecloud', 'GCP', 2.0),
    ('git', 'commit', 2.0), ('git', 'branch', 1.5),
    ('github', 'repository', 2.0), ('github', 'pull request', 1.5),
    ('gitlab', 'repository', 2.0), ('gitlab', 'CI/CD', 1.5),
    ('visualstudiocode', 'editor', 2.0), ('visualstudiocode', 'extension', 1.5),
    ('linux', 'operating system', 2.0), ('linux', 'terminal', 1.5),
    ('jwt', 'token', 2.0), ('jwt', 'authentication', 1.5),
    ('oauth', 'authorization', 2.0), ('oauth', 'access token', 1.5),
    ('json', 'data', 1.5), ('json', 'API', 1.5),
    ('html', 'web', 2.0), ('html', 'tag', 1.5),
    ('css', 'style', 2.0), ('css', 'frontend', 1.5),
    ('sql', 'database', 2.0), ('sql', 'query', 2.0)
)
insert into public.stt_term_contexts
    (term_id, context_text, normalized_text, weight, is_required)
select
    t.id,
    c.context_text,
    lower(trim(c.context_text)),
    c.weight,
    false
from context_data c
join public.stt_terms t using (normalized_key)
on conflict (term_id, normalized_text) do update set
    context_text = excluded.context_text,
    weight = excluded.weight;

commit;

-- Kiem tra so luong sau khi import.
select
    (select count(*) from public.stt_terms) as total_terms,
    (select count(*) from public.stt_term_pronunciations) as total_pronunciations,
    (select count(*) from public.stt_term_contexts) as total_contexts;
