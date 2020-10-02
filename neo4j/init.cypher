CREATE INDEX email_index FOR (e:Email)
ON (e.email);
CREATE INDEX text_index FOR (t:Text)
ON (t.text);
CREATE INDEX location_index FOR (l:Location)
ON (l.latitude, l.longitude);
CREATE INDEX media_index FOR (m:Media)
ON (m.checksum);
CREATE INDEX person_index FOR (p:Person)
ON (p.completeName);
CREATE INDEX phone_index FOR (p:Phone)
ON (p.phone);
CREATE INDEX ip_address_index FOR (i:IpAddress)
ON (i.ip);
CREATE INDEX social_media_post_index FOR (s:SocialMediaPost)
ON (s.id, s.platform);
CREATE INDEX user_account_index FOR (u:UserAccount)
ON (u.id, u.platform);
CREATE INDEX username_index FOR (u:Username)
ON (u.username);
CREATE INDEX domain_index FOR (d:Domain)
ON (d.domain);
CREATE INDEX keyword_index FOR (h:Keyword)
ON (h.keyword);
CREATE INDEX organization_index FOR (h:Organization)
ON (h.name);
CREATE INDEX hash_value_index FOR (h:HashValue)
ON (h.hashValue);

CREATE CONSTRAINT email_constraint
ON (e:Email) ASSERT e.nodeId IS UNIQUE;
CREATE CONSTRAINT ip_address_constraint
ON (i:IpAddress) ASSERT i.nodeId IS UNIQUE;
CREATE CONSTRAINT location_constraint
ON (l:Location) ASSERT l.nodeId IS UNIQUE;
CREATE CONSTRAINT media_constraint
ON (m:Media) ASSERT m.nodeId IS UNIQUE;
CREATE CONSTRAINT person_constraint
ON (p:Person) ASSERT p.nodeId IS UNIQUE;
CREATE CONSTRAINT phone_constraint
ON (p:Phone) ASSERT p.nodeId IS UNIQUE;
CREATE CONSTRAINT social_media_post_constraint
ON (s:SocialMediaPost) ASSERT s.nodeId IS UNIQUE;
CREATE CONSTRAINT text_constraint
ON (t:Text) ASSERT t.nodeId IS UNIQUE;
CREATE CONSTRAINT user_account_constraint
ON (u:UserAccount) ASSERT u.nodeId IS UNIQUE;
CREATE CONSTRAINT username_constraint
ON (u:Username) ASSERT u.nodeId IS UNIQUE;
CREATE CONSTRAINT domain_constraint
ON (d:Domain) ASSERT d.nodeId IS UNIQUE;
CREATE CONSTRAINT keyword_constraint
ON (h:Keyword) ASSERT h.nodeId IS UNIQUE;
CREATE CONSTRAINT organization_constraint
ON (h:Organization) ASSERT h.nodeId IS UNIQUE;
CREATE CONSTRAINT hash_value_constraint
ON (h:HashValue) ASSERT h.nodeId IS UNIQUE;