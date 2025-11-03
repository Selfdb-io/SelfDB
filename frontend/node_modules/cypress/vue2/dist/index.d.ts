/// <reference types="cypress" />

import Vue from 'vue';
import { Wrapper, VueTestUtilsConfigOptions } from '@vue/test-utils';
import { ComponentPublicInstanceConstructor } from 'vue/types/v3-component-public-instance';

/**
 * Type for component passed to "mount"
 *
 * @interface VueComponent
 * @example
 *  import Hello from './Hello.vue'
 *         ^^^^^ this type
 *  mount(Hello)
 */
type VueComponent = Vue.ComponentOptions<any> | Vue.VueConstructor | ComponentPublicInstanceConstructor;
/**
 * Options to pass to the component when creating it, like
 * props.
 *
 * @interface ComponentOptions
 */
type ComponentOptions = Record<string, unknown>;
type VueLocalComponents = Record<string, VueComponent>;
type VueFilters = {
    [key: string]: (value: string) => string;
};
type VueDirectives = {
    [key: string]: Function | Object;
};
type VueMixin = unknown;
type VueMixins = VueMixin | VueMixin[];
type VuePluginOptions = unknown;
type VuePlugin = unknown | [unknown, VuePluginOptions];
/**
 * A single Vue plugin or a list of plugins to register
 */
type VuePlugins = VuePlugin[];
/**
 * Additional Vue services to register while mounting the component, like
 * local components, plugins, etc.
 *
 * @interface MountOptionsExtensions
 * @see https://github.com/cypress-io/cypress/tree/develop/npm/vue#examples
 */
interface MountOptionsExtensions {
    /**
     * Extra local components
     *
     * @memberof MountOptionsExtensions
     * @see https://github.com/cypress-io/cypress/tree/develop/npm/vue#examples
     * @example
     *  import Hello from './Hello.vue'
     *  // imagine Hello needs AppComponent
     *  // that it uses in its template like <app-component ... />
     *  // during testing we can replace it with a mock component
     *  const appComponent = ...
     *  const components = {
     *    'app-component': appComponent
     *  },
     *  mount(Hello, { extensions: { components }})
     */
    components?: VueLocalComponents;
    /**
     * Optional Vue filters to install while mounting the component
     *
     * @memberof MountOptionsExtensions
     * @see https://github.com/cypress-io/cypress/tree/develop/npm/vue#examples
     * @example
     *  const filters = {
     *    reverse: (s) => s.split('').reverse().join(''),
     *  }
     *  mount(Hello, { extensions: { filters }})
     */
    filters?: VueFilters;
    /**
     * Optional Vue mixin(s) to install when mounting the component
     *
     * @memberof MountOptionsExtensions
     * @alias mixins
     * @see https://github.com/cypress-io/cypress/tree/develop/npm/vue#examples
     */
    mixin?: VueMixins;
    /**
     * Optional Vue mixin(s) to install when mounting the component
     *
     * @memberof MountOptionsExtensions
     * @alias mixin
     * @see https://github.com/cypress-io/cypress/tree/develop/npm/vue#examples
     */
    mixins?: VueMixins;
    /**
     * A single plugin or multiple plugins.
     *
     * @see https://github.com/cypress-io/cypress/tree/develop/npm/vue#examples
     * @alias plugins
     * @memberof MountOptionsExtensions
     */
    use?: VuePlugins;
    /**
     * A single plugin or multiple plugins.
     *
     * @see https://github.com/cypress-io/cypress/tree/develop/npm/vue#examples
     * @alias use
     * @memberof MountOptionsExtensions
     */
    plugins?: VuePlugins;
    /**
     * Optional Vue directives to install while mounting the component
     *
     * @memberof MountOptionsExtensions
     * @see https://github.com/cypress-io/cypress/tree/develop/npm/vue#examples
     * @example
     *  const directives = {
     *    custom: {
     *        name: 'custom',
     *        bind (el, binding) {
     *          el.dataset['custom'] = binding.value
     *        },
     *        unbind (el) {
     *          el.removeAttribute('data-custom')
     *        },
     *    },
     *  }
     *  mount(Hello, { extensions: { directives }})
     */
    directives?: VueDirectives;
}
/**
 * Options controlling how the component is going to be mounted,
 * including global Vue plugins and extensions.
 *
 * @interface MountOptions
 */
interface MountOptions {
    /**
     * Vue instance to use.
     *
     * @deprecated
     * @memberof MountOptions
     */
    vue: unknown;
    /**
     * Extra Vue plugins, mixins, local components to register while
     * mounting this component
     *
     * @memberof MountOptions
     * @see https://github.com/cypress-io/cypress/tree/develop/npm/vue#examples
     */
    extensions: MountOptionsExtensions;
}
/**
 * Utility type for union of options passed to "mount(..., options)"
 */
type MountOptionsArgument = Partial<ComponentOptions & MountOptions & VueTestUtilsConfigOptions>;
declare global {
    namespace Cypress {
        interface Cypress {
            /**
             * Mounted Vue instance is available under Cypress.vue
             * @memberof Cypress
             * @example
             *  mount(Greeting)
             *  .then(() => {
             *    Cypress.vue.message = 'Hello There'
             *  })
             *  // new message is displayed
             *  cy.contains('Hello There').should('be.visible')
             */
            vue: Vue;
            vueWrapper: Wrapper<Vue>;
        }
    }
}
/**
 * Mounts a Vue component inside Cypress browser.
 * @param {VueComponent} component imported from Vue file
 * @param {MountOptionsArgument} optionsOrProps used to pass options to component being mounted
 * @returns {Cypress.Chainable<{wrapper: Wrapper<T>, component: T}
 * @example
 * import { mount } from '@cypress/vue'
 * import { Stepper } from './Stepper.vue'
 *
 * it('mounts', () => {
 *   cy.mount(Stepper)
 *   cy.get('[data-cy=increment]').click()
 *   cy.get('[data-cy=counter]').should('have.text', '1')
 * })
 * @see {@link https://on.cypress.io/mounting-vue} for more details.
 *
 */
declare const mount: (component: VueComponent, optionsOrProps?: MountOptionsArgument) => Cypress.Chainable<{
    wrapper: Wrapper<Vue, Element>;
    component: Wrapper<Vue, Element>['vm'];
}>;
/**
 * Helper function for mounting a component quickly in test hooks.
 * @example
 *  import {mountCallback} from '@cypress/vue2'
 *  beforeEach(mountVue(component, options))
 *
 * Removed as of Cypress 11.0.0.
 * @see https://on.cypress.io/migration-11-0-0-component-testing-updates
 */
declare const mountCallback: (component: VueComponent, options?: MountOptionsArgument) => () => void;

export { mount, mountCallback };
