describe('View participant badge', function() {
  const usher = require('../fixtures/user.json').usher;
  const profile = require('../fixtures/profile.json');
  const project = require('../fixtures/project.json');
  const events = require('../fixtures/events.json');
  const participants = require('../fixtures/participants.json');

  it('View participant badge', function() {
    cy.server();
    cy.route('POST', '**/participants/checkin?*').as('checkin');
    cy.route('**/participants/json').as('participant-list');

    cy.login('/', usher.username, usher.password);

    cy.get('[data-cy-title="' + project.title + '"]')
      .first()
      .click();
    cy.location('pathname').should('contain', project.url);
    cy.get('a[data-cy-navbar="settings"]').click();
    cy.location('pathname').should('contain', 'settings');
    cy.get('a[data-cy="setup-events"').click();
    cy.location('pathname').should('contain', '/admin');
    cy.get('a[data-cy="' + events[1].title + '"]').click();
    var firstname = participants[2].fullname.split(' ')[0];
    cy.get('td[data-cy="participant"]')
      .contains(participants[2].fullname)
      .parent()
      .find('a[data-cy="show-badge"]')
      .invoke('removeAttr', 'target')
      .click();
    cy.url().should('contain', 'badge');
    cy.get('.first-name').should('contain', firstname);
    cy.screenshot('badge');
  });
});
