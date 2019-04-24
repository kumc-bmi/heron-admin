Object capability (ocap) discipline
-----------------------------------

In order to supporting robust composition and cooperation without
vulnerability, code in this project should adhere to [object
capability discipline][ocap].

  - **Memory safety and encapsulation**
    - There is no way to get a reference to an object except by
      creating one or being given one at creation or via a message; no
      casting integers to pointers, for example. *Python is safe
      in this way.*

      From outside an object, there is no way to access the internal
      state of the object without the object's consent (where consent
      is expressed by responding to messages). *We approximate this
      with various idioms. WIP.*

  - **Primitive effects only via references**
    - The only way an object can affect the world outside itself is
      via references to other objects. All primitives for interacting
      with the external world are embodied by primitive objects and
      **anything globally accessible is immutable data**. There must
      be no `open(filename)` function in the global namespace, nor may
      such a function be imported. *It takes some discipline to use
      python in this way.  We use a convention of only accessing
      ambient authority inside `if __name__ == '__main__':`.* module)
      { ... }`._

[ocap]: http://erights.org/elib/capability/ode/ode-capabilities.html
